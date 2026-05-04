import asyncio
import base64
import logging
import os
import re
import shutil
import signal
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ----------------------------
# Settings
# ----------------------------


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str = "sk-local"
    model_id: str = "flux-klein-4b"

    model_path: Path = Path("/models/flux-2-klein-4b-Q4_K_M.gguf")
    vae_path: Path = Path("/models/flux2_ae.safetensors")
    llm_path: Path = Path("/models/qwen_3_4b.safetensors")

    output_dir: Path = Path("/data/outputs")
    public_base_url: str = "http://localhost:8000"

    max_concurrent_jobs: int = 1
    queue_maxsize: int = 16
    job_timeout_seconds: int = 1800
    retention_hours: int = 72

    default_steps: int = 4
    default_cfg_scale: float = 1.0
    default_sampler: str = "euler"
    default_rng: str = "cuda"
    default_guidance: Optional[float] = None
    default_threads: int = 0

    enable_offload_to_cpu: bool = True
    enable_diffusion_fa: bool = True
    enable_mmap: bool = False
    disable_image_metadata: bool = False

    log_level: str = "INFO"


settings = Settings()
settings.output_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("flux-api")


# ----------------------------
# Metrics
# ----------------------------

REQUEST_COUNTER = Counter(
    "flux_api_requests_total", "Total API requests", ["endpoint", "method", "status"]
)
JOB_COUNTER = Counter("flux_api_jobs_total", "Total jobs", ["status"])
JOB_DURATION = Histogram(
    "flux_api_job_duration_seconds", "Image generation job duration"
)
QUEUE_DEPTH = Gauge("flux_api_queue_depth", "Current job queue depth")
RUNNING_JOBS = Gauge("flux_api_running_jobs", "Currently running jobs")


# ----------------------------
# Models
# ----------------------------


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImageGenerationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    model: Optional[str] = None
    prompt: str = Field(..., min_length=1)
    negative_prompt: str = ""
    n: int = Field(default=1, ge=1, le=8)
    size: str = "1024x1024"
    response_format: Literal["url", "b64_json"] = "url"

    # OpenAI-compatible endpoint, plus useful local extensions:
    step: Optional[int] = Field(default=None, ge=1, le=100)
    steps: Optional[int] = Field(default=None, ge=1, le=100)
    cfg_scale: Optional[float] = Field(default=None, ge=0.0, le=50.0)
    guidance: Optional[float] = Field(default=None, ge=0.0, le=50.0)
    seed: int = -1
    sampling_method: Optional[str] = None
    user: Optional[str] = None
    async_mode: bool = Field(default=False, alias="async")

    def effective_steps(self) -> int:
        return self.steps or self.step or settings.default_steps

    def effective_cfg_scale(self) -> float:
        return (
            self.cfg_scale if self.cfg_scale is not None else settings.default_cfg_scale
        )

    def effective_sampler(self) -> str:
        return self.sampling_method or settings.default_sampler


class ImageData(BaseModel):
    url: Optional[str] = None
    b64_json: Optional[str] = None
    revised_prompt: Optional[str] = None


class ImageGenerationResponse(BaseModel):
    created: int
    data: list[ImageData]


class JobResponse(BaseModel):
    id: str
    status: JobStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None


@dataclass
class JobRecord:
    id: str
    request: ImageGenerationRequest
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    future: asyncio.Future = field(default_factory=asyncio.Future)
    work_dir: Optional[Path] = None


# ----------------------------
# Helpers
# ----------------------------


def verify_api_key(authorization: Optional[str] = Header(default=None)) -> None:
    if not settings.api_key:
        return
    expected = f"Bearer {settings.api_key}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


def parse_size(size: str) -> tuple[int, int]:
    m = re.fullmatch(r"(\d{2,5})x(\d{2,5})", size.strip().lower())
    if not m:
        raise HTTPException(status_code=422, detail="size must be like '1024x1024'")
    width = int(m.group(1))
    height = int(m.group(2))
    if width < 64 or height < 64 or width > 4096 or height > 4096:
        raise HTTPException(status_code=422, detail="size out of allowed range")
    return width, height


def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def abs_file_url(request: Request, relative_path: str) -> str:
    # Serve under /files/{path}
    return str(request.url_for("files", path=relative_path))


def file_to_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def tail(text: bytes, limit: int = 6000) -> str:
    try:
        s = text.decode("utf-8", errors="replace")
    except Exception:
        s = repr(text)
    return s[-limit:]


# ----------------------------
# Job manager
# ----------------------------


class JobManager:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[JobRecord] = asyncio.Queue(
            maxsize=settings.queue_maxsize
        )
        self.jobs: dict[str, JobRecord] = {}
        self.workers: list[asyncio.Task] = []
        self.cleanup_task: Optional[asyncio.Task] = None
        self.active_processes: dict[str, asyncio.subprocess.Process] = {}
        self._shutdown = False

    async def start(self) -> None:
        for idx in range(settings.max_concurrent_jobs):
            self.workers.append(asyncio.create_task(self.worker_loop(idx)))
        self.cleanup_task = asyncio.create_task(self.cleanup_loop())
        logger.info(
            "Job manager started with %s worker(s)", settings.max_concurrent_jobs
        )

    async def stop(self) -> None:
        self._shutdown = True

        for job_id, proc in list(self.active_processes.items()):
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except Exception:
                pass

        for task in self.workers:
            task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()

        await asyncio.gather(*self.workers, return_exceptions=True)
        if self.cleanup_task:
            await asyncio.gather(self.cleanup_task, return_exceptions=True)

    async def submit(self, req: ImageGenerationRequest) -> JobRecord:
        if self.queue.full():
            raise HTTPException(status_code=503, detail="Queue is full")

        job = JobRecord(id=str(uuid.uuid4()), request=req)
        job.work_dir = settings.output_dir / job.id
        job.work_dir.mkdir(parents=True, exist_ok=True)

        self.jobs[job.id] = job
        await self.queue.put(job)
        QUEUE_DEPTH.set(self.queue.qsize())
        logger.info("Queued job=%s", job.id)
        return job

    async def cancel(self, job_id: str) -> JobRecord:
        job = self.jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}:
            return job

        if job.status == JobStatus.RUNNING and job_id in self.active_processes:
            proc = self.active_processes[job_id]
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now(timezone.utc)
            job.error = "Cancelled by user"
            if not job.future.done():
                job.future.cancel()
            JOB_COUNTER.labels(status="cancelled").inc()
            return job

        if job.status == JobStatus.QUEUED:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now(timezone.utc)
            job.error = "Cancelled by user"
            if not job.future.done():
                job.future.cancel()
            JOB_COUNTER.labels(status="cancelled").inc()

        return job

    async def worker_loop(self, worker_idx: int) -> None:
        while True:
            job = await self.queue.get()
            QUEUE_DEPTH.set(self.queue.qsize())

            if job.status == JobStatus.CANCELLED:
                self.queue.task_done()
                continue

            start_ts = time.perf_counter()
            RUNNING_JOBS.inc()
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)

            logger.info("Worker=%s starting job=%s", worker_idx, job.id)

            try:
                result = await self._run_job(job)
                job.result = result
                job.status = JobStatus.SUCCEEDED
                JOB_COUNTER.labels(status="succeeded").inc()
                if not job.future.done():
                    job.future.set_result(result)
            except asyncio.CancelledError:
                job.status = JobStatus.CANCELLED
                job.error = "Cancelled"
                JOB_COUNTER.labels(status="cancelled").inc()
                if not job.future.done():
                    job.future.cancel()
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
                JOB_COUNTER.labels(status="failed").inc()
                if not job.future.done():
                    job.future.set_exception(e)
                logger.exception("Job=%s failed", job.id)
            finally:
                job.completed_at = datetime.now(timezone.utc)
                self.active_processes.pop(job.id, None)
                RUNNING_JOBS.dec()
                JOB_DURATION.observe(time.perf_counter() - start_ts)
                self.queue.task_done()

    async def _run_job(self, job: JobRecord) -> dict[str, Any]:
        req = job.request
        width, height = parse_size(req.size)

        output_pattern = str(job.work_dir / "image_%03d.png")
        seed = req.seed if req.seed is not None else -1

        cmd = [
            "sd-cli",
            "--diffusion-model",
            str(settings.model_path),
            "--vae",
            str(settings.vae_path),
            "--llm",
            str(settings.llm_path),
            "-p",
            req.prompt,
            "-n",
            req.negative_prompt,
            "-o",
            output_pattern,
            "-W",
            str(width),
            "-H",
            str(height),
            "--steps",
            str(req.effective_steps()),
            "--cfg-scale",
            str(req.effective_cfg_scale()),
            "-s",
            str(seed),
            "-b",
            str(req.n),
            "--sampling-method",
            req.effective_sampler(),
            "--rng",
            settings.default_rng,
        ]

        if req.guidance is not None:
            cmd.extend(["--guidance", str(req.guidance)])
        elif settings.default_guidance is not None:
            cmd.extend(["--guidance", str(settings.default_guidance)])

        if settings.default_threads and settings.default_threads > 0:
            cmd.extend(["-t", str(settings.default_threads)])

        if settings.enable_offload_to_cpu:
            cmd.append("--offload-to-cpu")

        if settings.enable_diffusion_fa:
            cmd.append("--diffusion-fa")

        if settings.enable_mmap:
            cmd.append("--mmap")

        if settings.disable_image_metadata:
            cmd.append("--disable-image-metadata")

        logger.info("Job=%s command=%s", job.id, " ".join(cmd))

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(job.work_dir),
            start_new_session=True,
        )
        self.active_processes[job.id] = proc

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=settings.job_timeout_seconds,
            )
        except asyncio.TimeoutError:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                pass
            raise RuntimeError(f"Job timed out after {settings.job_timeout_seconds}s")

        if job.status == JobStatus.CANCELLED:
            raise asyncio.CancelledError()

        if proc.returncode != 0:
            raise RuntimeError(
                f"sd-cli exited with code {proc.returncode}\n"
                f"stderr:\n{tail(stderr)}\n"
                f"stdout:\n{tail(stdout)}"
            )

        files = sorted(job.work_dir.glob("image_*.png"))
        if not files:
            # fallback if a single image is produced differently
            files = sorted(job.work_dir.glob("*.png"))

        if not files:
            raise RuntimeError("No output image was produced")

        relative_files = [
            str(p.relative_to(settings.output_dir).as_posix()) for p in files
        ]

        return {
            "created": int(time.time()),
            "files": relative_files,
            "meta": {
                "job_id": job.id,
                "steps": req.effective_steps(),
                "cfg_scale": req.effective_cfg_scale(),
                "sampling_method": req.effective_sampler(),
                "seed": seed,
                "n": req.n,
                "size": req.size,
            },
        }

    async def cleanup_loop(self) -> None:
        while True:
            await asyncio.sleep(3600)
            try:
                cutoff = time.time() - settings.retention_hours * 3600
                for child in settings.output_dir.iterdir():
                    try:
                        if child.is_dir() and child.stat().st_mtime < cutoff:
                            shutil.rmtree(child, ignore_errors=True)
                    except FileNotFoundError:
                        pass
            except Exception:
                logger.exception("Cleanup loop failed")


manager = JobManager()


# ----------------------------
# FastAPI app
# ----------------------------

app = FastAPI(title="FLUX.2-klein stable-diffusion.cpp API", version="1.0.0")
app.mount("/files", StaticFiles(directory=str(settings.output_dir)), name="files")


@app.on_event("startup")
async def startup_event() -> None:
    missing = [
        p
        for p in [settings.model_path, settings.vae_path, settings.llm_path]
        if not p.exists()
    ]
    if missing:
        raise RuntimeError(f"Missing model file(s): {', '.join(map(str, missing))}")

    # Verify the binary is callable
    proc = await asyncio.create_subprocess_exec(
        "sd-cli",
        "--help",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError("sd-cli is not working")

    await manager.start()
    logger.info("Startup complete")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await manager.stop()
    logger.info("Shutdown complete")


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        REQUEST_COUNTER.labels(
            endpoint=request.url.path,
            method=request.method,
            status=str(response.status_code),
        ).inc()
        return response
    except Exception:
        REQUEST_COUNTER.labels(
            endpoint=request.url.path,
            method=request.method,
            status="500",
        ).inc()
        raise


@app.get("/health/live")
async def health_live():
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready():
    ok = (
        settings.model_path.exists()
        and settings.vae_path.exists()
        and settings.llm_path.exists()
    )
    if not ok:
        raise HTTPException(status_code=503, detail="Model files not ready")
    return {
        "status": "ready",
        "model_id": settings.model_id,
        "queue_depth": manager.queue.qsize(),
        "max_concurrent_jobs": settings.max_concurrent_jobs,
    }


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/v1/models", dependencies=[Depends(verify_api_key)])
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": settings.model_id,
                "object": "model",
                "owned_by": "local",
            }
        ],
    }


@app.get(
    "/v1/jobs/{job_id}",
    response_model=JobResponse,
    dependencies=[Depends(verify_api_key)],
)
async def get_job(job_id: str):
    job = manager.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        id=job.id,
        status=job.status,
        created_at=iso(job.created_at),
        started_at=iso(job.started_at),
        completed_at=iso(job.completed_at),
        error=job.error,
        result=job.result,
    )


@app.post(
    "/v1/jobs/{job_id}/cancel",
    response_model=JobResponse,
    dependencies=[Depends(verify_api_key)],
)
async def cancel_job(job_id: str):
    job = await manager.cancel(job_id)
    return JobResponse(
        id=job.id,
        status=job.status,
        created_at=iso(job.created_at),
        started_at=iso(job.started_at),
        completed_at=iso(job.completed_at),
        error=job.error,
        result=job.result,
    )


@app.post("/v1/images/generations", dependencies=[Depends(verify_api_key)])
async def create_image(request: Request, body: ImageGenerationRequest):
    if body.model and body.model != settings.model_id:
        raise HTTPException(status_code=400, detail=f"Unknown model '{body.model}'")

    job = await manager.submit(body)

    if body.async_mode:
        return JSONResponse(
            status_code=202,
            content={
                "id": job.id,
                "status": job.status,
                "created_at": iso(job.created_at),
            },
        )

    try:
        result = await job.future
    except asyncio.CancelledError:
        raise HTTPException(status_code=499, detail="Job cancelled")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    files = result["files"]
    data: list[ImageData] = []

    for rel in files:
        abs_path = settings.output_dir / rel
        if body.response_format == "b64_json":
            data.append(
                ImageData(
                    b64_json=file_to_b64(abs_path),
                    revised_prompt=body.prompt,
                )
            )
        else:
            data.append(
                ImageData(
                    url=abs_file_url(request, rel),
                    revised_prompt=body.prompt,
                )
            )

    return ImageGenerationResponse(
        created=result["created"],
        data=data,
    )
