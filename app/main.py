import asyncio
import base64
import json
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

import httpx
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
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ----------------------------
# Settings
# ----------------------------


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str = "sk-local"
    model_id: str = "flux-klein-4b"

    model_path: Path = Path("/models/flux-2-klein-4b-Q4_0.gguf")
    vae_path: Optional[Path] = Path("/models/flux2-vae.safetensors")
    taesd_path: Optional[Path] = None
    llm_path: Path = Path("/models/Qwen3-4B-UD-Q4_K_XL.gguf")

    output_dir: Path = Path("/data/outputs")
    public_base_url: str = ""
    sd_server_listen_ip: str = "127.0.0.1"
    sd_server_port: int = 1234
    sd_server_start_timeout_seconds: int = 120
    sd_server_poll_interval_seconds: float = 1.0

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

    @field_validator("default_guidance", mode="before")
    @classmethod
    def empty_guidance_as_none(cls, value: Any) -> Any:
        if value == "":
            return None
        return value

    @field_validator("vae_path", "taesd_path", mode="before")
    @classmethod
    def empty_path_as_none(cls, value: Any) -> Any:
        if value == "":
            return None
        return value


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


class ModelCard(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str
    permission: list[dict[str, Any]] = Field(default_factory=list)
    root: str
    parent: Optional[str] = None


class ModelListResponse(BaseModel):
    object: Literal["list"] = "list"
    data: list[ModelCard]


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
    backend_job_id: Optional[str] = None


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


def build_model_card() -> ModelCard:
    created = int(time.time())
    try:
        created = int(settings.model_path.stat().st_mtime)
    except OSError:
        pass

    return ModelCard(
        id=settings.model_id,
        created=created,
        owned_by="local",
        root=settings.model_id,
        parent=None,
    )


def sd_server_base_url() -> str:
    host = settings.sd_server_listen_ip
    if host == "0.0.0.0":
        host = "127.0.0.1"
    return f"http://{host}:{settings.sd_server_port}"


def summarize_backend_error(payload: Any) -> str:
    if isinstance(payload, dict):
        error = payload.get("error")
        message = payload.get("message")
        if isinstance(error, dict):
            code = error.get("code")
            backend_message = error.get("message")
            if code and backend_message:
                return f"{code}: {backend_message}"
            if backend_message:
                return str(backend_message)
        if error and message:
            return f"{error}: {message}"
        if error:
            return str(error)
        if message:
            return str(message)
    if isinstance(payload, (dict, list)):
        return json.dumps(payload)
    return str(payload)


def build_backend_img_gen_payload(
    image_request: ImageGenerationRequest, width: int, height: int
) -> dict[str, Any]:
    guidance: dict[str, Any] = {"txt_cfg": image_request.effective_cfg_scale()}
    effective_guidance = (
        image_request.guidance
        if image_request.guidance is not None
        else settings.default_guidance
    )
    if effective_guidance is not None:
        guidance["distilled_guidance"] = effective_guidance

    return {
        "prompt": image_request.prompt,
        "negative_prompt": image_request.negative_prompt,
        "width": width,
        "height": height,
        "seed": image_request.seed,
        "batch_count": image_request.n,
        "embed_image_metadata": not settings.disable_image_metadata,
        "sample_params": {
            "sample_method": image_request.effective_sampler(),
            "sample_steps": image_request.effective_steps(),
            "guidance": guidance,
        },
        "output_format": "png",
        "output_compression": 100,
    }


def abs_file_url(request: Request, relative_path: str) -> str:
    file_path = str(request.app.url_path_for("files", path=relative_path))
    public_base_url = settings.public_base_url.strip().rstrip("/")
    if public_base_url:
        return f"{public_base_url}{file_path}"
    return str(request.url_for("files", path=relative_path))


def file_to_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def tail(text: bytes, limit: int = 6000) -> str:
    try:
        s = text.decode("utf-8", errors="replace")
    except Exception:
        s = repr(text)
    return s[-limit:]


def required_asset_paths() -> dict[str, Path]:
    paths: dict[str, Path] = {
        "diffusion_model": settings.model_path,
        "llm": settings.llm_path,
    }

    mode = decoder_mode()
    if mode == "vae" and settings.vae_path is not None:
        paths["vae"] = settings.vae_path
    if mode == "taesd" and settings.taesd_path is not None:
        paths["taesd"] = settings.taesd_path
    return paths


def decoder_mode() -> str:
    if settings.vae_path is not None:
        return "vae"
    if settings.taesd_path is not None:
        return "taesd"
    raise RuntimeError("Either VAE_PATH or TAESD_PATH must be configured")


def missing_required_assets() -> dict[str, str]:
    return {
        name: str(path)
        for name, path in required_asset_paths().items()
        if not path.exists()
    }


# ----------------------------
# Job manager
# ----------------------------


class SDServerManager:
    def __init__(self) -> None:
        self.process: Optional[asyncio.subprocess.Process] = None
        self.client: Optional[httpx.AsyncClient] = None

    def _build_command(self) -> list[str]:
        cmd = [
            "sd-server",
            "--listen-ip",
            settings.sd_server_listen_ip,
            "--listen-port",
            str(settings.sd_server_port),
            "--diffusion-model",
            str(settings.model_path),
            "--llm",
            str(settings.llm_path),
            "--steps",
            str(settings.default_steps),
            "--cfg-scale",
            str(settings.default_cfg_scale),
            "--sampling-method",
            settings.default_sampler,
            "--rng",
            settings.default_rng,
        ]

        if decoder_mode() == "taesd":
            cmd.extend(["--taesd", str(settings.taesd_path)])
        else:
            cmd.extend(["--vae", str(settings.vae_path)])

        if settings.default_guidance is not None:
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

        if logger.isEnabledFor(logging.DEBUG):
            cmd.append("-v")

        return cmd

    def _ensure_client(self) -> httpx.AsyncClient:
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=sd_server_base_url(),
                timeout=httpx.Timeout(10.0, connect=5.0),
            )
        return self.client

    def _ensure_running(self) -> None:
        if self.process is None:
            raise RuntimeError("sd-server has not been started")
        if self.process.returncode is not None:
            raise RuntimeError(f"sd-server exited with code {self.process.returncode}")

    @staticmethod
    def _parse_response_payload(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text.strip() or {"error": f"HTTP {response.status_code}"}

    async def start(self) -> None:
        if self.process is not None and self.process.returncode is None:
            return

        self._ensure_client()
        cmd = self._build_command()
        logger.info("Starting sd-server: %s", " ".join(cmd))
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            start_new_session=True,
        )
        try:
            await self.wait_until_ready()
        except Exception:
            await self.stop()
            raise

    async def stop(self) -> None:
        if self.client is not None:
            await self.client.aclose()
            self.client = None

        if self.process is None:
            return

        if self.process.returncode is None:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

            try:
                await asyncio.wait_for(self.process.wait(), timeout=10)
            except asyncio.TimeoutError:
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await self.process.wait()

        self.process = None

    async def restart(self) -> None:
        """Stop and restart the sd-server. Used for self-healing."""
        logger.warning("sd-server appears unhealthy, attempting restart...")
        await self.stop()
        # Small delay to allow port release
        await asyncio.sleep(2)
        await self.start()
        logger.info("sd-server restart complete")

    async def wait_until_ready(self) -> dict[str, Any]:
        client = self._ensure_client()
        loop = asyncio.get_running_loop()
        deadline = loop.time() + settings.sd_server_start_timeout_seconds
        last_error = "unknown startup error"

        while loop.time() < deadline:
            self._ensure_running()
            try:
                response = await client.get("/sdcpp/v1/capabilities")
                payload = self._parse_response_payload(response)
                if response.status_code == 200 and isinstance(payload, dict):
                    return payload
                last_error = summarize_backend_error(payload)
            except Exception as exc:
                last_error = str(exc)
                if self.process is not None and self.process.returncode is not None:
                    raise RuntimeError(last_error) from exc

            await asyncio.sleep(0.5)

        raise RuntimeError(
            "sd-server did not become ready within "
            f"{settings.sd_server_start_timeout_seconds}s: {last_error}"
        )

    async def capabilities(self) -> dict[str, Any]:
        self._ensure_running()
        response = await self._ensure_client().get("/sdcpp/v1/capabilities")
        payload = self._parse_response_payload(response)
        if response.status_code != 200 or not isinstance(payload, dict):
            raise RuntimeError(
                f"sd-server capabilities failed ({response.status_code}): "
                f"{summarize_backend_error(payload)}"
            )
        return payload

    async def submit_img_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_running()
        response = await self._ensure_client().post("/sdcpp/v1/img_gen", json=payload)
        response_payload = self._parse_response_payload(response)
        if response.status_code != 202 or not isinstance(response_payload, dict):
            raise RuntimeError(
                f"sd-server job submission failed ({response.status_code}): "
                f"{summarize_backend_error(response_payload)}"
            )
        return response_payload

    async def get_job(self, backend_job_id: str) -> dict[str, Any]:
        self._ensure_running()
        response = await self._ensure_client().get(f"/sdcpp/v1/jobs/{backend_job_id}")
        payload = self._parse_response_payload(response)
        if response.status_code != 200 or not isinstance(payload, dict):
            raise RuntimeError(
                f"sd-server job lookup failed ({response.status_code}): "
                f"{summarize_backend_error(payload)}"
            )
        return payload

    async def cancel_job(self, backend_job_id: str) -> tuple[int, Any]:
        self._ensure_running()
        response = await self._ensure_client().post(
            f"/sdcpp/v1/jobs/{backend_job_id}/cancel"
        )
        return response.status_code, self._parse_response_payload(response)


class JobManager:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[JobRecord] = asyncio.Queue(
            maxsize=settings.queue_maxsize
        )
        self.jobs: dict[str, JobRecord] = {}
        self.workers: list[asyncio.Task] = []
        self.cleanup_task: Optional[asyncio.Task] = None
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

    @staticmethod
    def _mark_cancelled(job: JobRecord, error: str) -> None:
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now(timezone.utc)
        job.error = error
        if not job.future.done():
            job.future.cancel()

    async def cancel(self, job_id: str) -> JobRecord:
        job = self.jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}:
            return job

        if job.status == JobStatus.RUNNING:
            if job.backend_job_id is None:
                self._mark_cancelled(job, "Cancelled by user")
                JOB_COUNTER.labels(status="cancelled").inc()
                return job

            status_code, payload = await sd_server.cancel_job(job.backend_job_id)
            if status_code == 200:
                self._mark_cancelled(job, "Cancelled by user")
                JOB_COUNTER.labels(status="cancelled").inc()
                return job
            if status_code == 409:
                raise HTTPException(
                    status_code=409,
                    detail=summarize_backend_error(payload),
                )
            raise HTTPException(
                status_code=502,
                detail=(
                    f"sd-server cancellation failed: {summarize_backend_error(payload)}"
                ),
            )

        if job.status == JobStatus.QUEUED:
            self._mark_cancelled(job, "Cancelled by user")
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
                RUNNING_JOBS.dec()
                JOB_DURATION.observe(time.perf_counter() - start_ts)
                self.queue.task_done()

    def _store_backend_result(
        self, job: JobRecord, backend_job: dict[str, Any]
    ) -> dict[str, Any]:
        result = backend_job.get("result") or {}
        images = result.get("images") or []
        output_format = result.get("output_format") or "png"

        if not images:
            raise RuntimeError("sd-server completed without images")

        files: list[Path] = []
        for index, image in enumerate(images, start=1):
            b64_data = image.get("b64_json")
            if not b64_data:
                continue
            file_path = job.work_dir / f"image_{index:03d}.{output_format}"
            try:
                file_path.write_bytes(base64.b64decode(b64_data))
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to decode generated image #{index}: {exc}"
                ) from exc
            files.append(file_path)

        if not files:
            raise RuntimeError("sd-server returned no decodable image outputs")

        req = job.request
        relative_files = [
            str(path.relative_to(settings.output_dir).as_posix()) for path in files
        ]

        return {
            "created": int(time.time()),
            "files": relative_files,
            "meta": {
                "job_id": job.id,
                "backend_job_id": job.backend_job_id,
                "steps": req.effective_steps(),
                "cfg_scale": req.effective_cfg_scale(),
                "sampling_method": req.effective_sampler(),
                "seed": req.seed,
                "n": req.n,
                "size": req.size,
                "output_format": output_format,
            },
        }

    async def _run_job(self, job: JobRecord) -> dict[str, Any]:
        if job.status == JobStatus.CANCELLED:
            raise asyncio.CancelledError()

        req = job.request
        width, height = parse_size(req.size)
        backend_request = build_backend_img_gen_payload(req, width, height)
        submission = await sd_server.submit_img_job(backend_request)
        job.backend_job_id = submission.get("id")

        if not job.backend_job_id:
            raise RuntimeError("sd-server did not return a job id")

        if job.status == JobStatus.CANCELLED:
            status_code, payload = await sd_server.cancel_job(job.backend_job_id)
            if status_code == 409:
                logger.warning(
                    "Cancelled local job=%s after backend job=%s had already started: %s",
                    job.id,
                    job.backend_job_id,
                    summarize_backend_error(payload),
                )
            raise asyncio.CancelledError()

        logger.info(
            "Job=%s delegated to sd-server job=%s",
            job.id,
            job.backend_job_id,
        )

        loop = asyncio.get_running_loop()
        deadline = loop.time() + settings.job_timeout_seconds

        while True:
            if job.status == JobStatus.CANCELLED:
                raise asyncio.CancelledError()

            if loop.time() >= deadline:
                try:
                    status_code, payload = await sd_server.cancel_job(
                        job.backend_job_id
                    )
                    if status_code == 409:
                        logger.warning(
                            "Timed out job=%s while backend job=%s was already generating: %s",
                            job.id,
                            job.backend_job_id,
                            summarize_backend_error(payload),
                        )
                except Exception:
                    logger.exception(
                        "Failed to cancel timed out backend job=%s",
                        job.backend_job_id,
                    )
                raise RuntimeError(
                    f"Job timed out after {settings.job_timeout_seconds}s"
                )

            backend_job = await sd_server.get_job(job.backend_job_id)
            backend_status = backend_job.get("status")

            if backend_status == "completed":
                return self._store_backend_result(job, backend_job)
            if backend_status == "failed":
                raise RuntimeError(
                    summarize_backend_error(backend_job.get("error") or backend_job)
                )
            if backend_status == "cancelled":
                raise asyncio.CancelledError()
            if backend_status not in {"queued", "generating"}:
                raise RuntimeError(
                    f"Unexpected sd-server job status '{backend_status}'"
                )

            await asyncio.sleep(settings.sd_server_poll_interval_seconds)

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


sd_server = SDServerManager()
manager = JobManager()


# ----------------------------
# FastAPI app
# ----------------------------

app = FastAPI(title="FLUX.2-klein stable-diffusion.cpp API", version="1.0.0")
app.mount("/files", StaticFiles(directory=str(settings.output_dir)), name="files")


@app.on_event("startup")
async def startup_event() -> None:
    decoder_mode()
    missing = missing_required_assets()
    if missing:
        details = ", ".join(f"{name}={path}" for name, path in missing.items())
        raise RuntimeError(f"Missing model file(s): {details}")

    await sd_server.start()
    await manager.start()
    logger.info("Startup complete; backend=%s", sd_server_base_url())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await manager.stop()
    await sd_server.stop()
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
    missing = missing_required_assets()
    if missing:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Model files not ready",
                "missing": missing,
            },
        )

    try:
        capabilities = await sd_server.capabilities()
    except Exception as exc:
        # Attempt self-healing: restart sd-server
        try:
            await sd_server.restart()
            # After restart, check again
            capabilities = await sd_server.capabilities()
        except Exception as retry_exc:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "sd-server is not ready, recovery failed",
                    "error": str(exc),
                    "recovery_error": str(retry_exc),
                },
            ) from exc

    return {
        "status": "ready",
        "model_id": settings.model_id,
        "assets": {name: str(path) for name, path in required_asset_paths().items()},
        "backend": {
            "url": sd_server_base_url(),
            "model": capabilities.get("model"),
        },
        "queue_depth": manager.queue.qsize(),
        "max_concurrent_jobs": settings.max_concurrent_jobs,
    }


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get(
    "/v1/models",
    response_model=ModelListResponse,
    dependencies=[Depends(verify_api_key)],
)
async def list_models() -> ModelListResponse:
    return ModelListResponse(data=[build_model_card()])


@app.get(
    "/v1/models/{model_id}",
    response_model=ModelCard,
    dependencies=[Depends(verify_api_key)],
)
async def get_model(model_id: str) -> ModelCard:
    if model_id != settings.model_id:
        raise HTTPException(status_code=404, detail="Model not found")
    return build_model_card()


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
