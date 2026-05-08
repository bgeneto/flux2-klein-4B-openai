"""
Thin FastAPI proxy for SGLang Z-Image Turbo endpoint.

Provides:
- Health checks (/health/live, /health/ready)
- API key authentication
- Metrics endpoint (/metrics)
- Direct proxy to SGLang OpenAI-compatible API
"""

import json
import logging
import os
import time
from typing import Any, Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

# ----------------------------
# Settings
# ----------------------------


class Settings:
    model_config = {"env_file": ".env", "extra": "ignore"}

    api_key: str = os.getenv("API_KEY", "sk-local")
    sglang_url: str = os.getenv("SGLANG_URL", "http://localhost:30010")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("zimage-api")

# ----------------------------
# Metrics
# ----------------------------

REQUEST_COUNTER = Counter(
    "zimage_api_requests_total", "Total API requests", ["endpoint", "method", "status"]
)

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


async def proxy_request(method: str, path: str, request: Request, body: Any = None):
    """Forward a request to the SGLang backend and return the response."""
    target_url = f"{settings.sglang_url.rstrip('/')}/{path.lstrip('/')}"

    headers = {key: value for key, value in request.headers.items() if key.lower() not in ("host", "transfer-encoding", "connection")}
    headers["Authorization"] = f"Bearer {settings.api_key}"

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            if method in ("POST", "PUT", "PATCH"):
                response = await client.request(
                    method=method,
                    url=target_url,
                    headers=headers,
                    json=body,
                )
            else:
                response = await client.request(
                    method=method,
                    url=target_url,
                    headers=headers,
                )

            # Update metrics
            REQUEST_COUNTER.labels(
                endpoint=path,
                method=method,
                status=str(response.status_code),
            ).inc()

            content = await response.aread()
            content_type = response.headers.get("content-type", "application/json")

            if "application/json" in content_type:
                return JSONResponse(
                    content=json.loads(content),
                    status_code=response.status_code,
                    headers=dict(response.headers),
                )
            else:
                return Response(
                    content=content,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                )
        except httpx.HTTPStatusError as e:
            REQUEST_COUNTER.labels(
                endpoint=path,
                method=method,
                status=str(e.response.status_code),
            ).inc()
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"SGLang backend error: {e.response.text}",
            )
        except httpx.ConnectError:
            raise HTTPException(
                status_code=502,
                detail=f"Cannot connect to SGLang backend at {settings.sglang_url}",
            )


# ----------------------------
# FastAPI app
# ----------------------------

app = FastAPI(
    title="Z-Image Turbo SGLang API",
    version="1.0.0",
    description="Thin proxy to SGLang Z-Image Turbo OpenAI-compatible endpoint",
)


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
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.sglang_url.rstrip('/')}/v1/models")
            if response.status_code == 200:
                return {"status": "ready", "sglang_url": settings.sglang_url}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "SGLang backend is not ready",
                "error": str(exc),
            },
        ) from exc

    raise HTTPException(
        status_code=503,
        detail="SGLang backend returned non-200 status",
    )


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ----------------------------
# SGLang proxy endpoints
# ----------------------------


@app.get("/v1/models", dependencies=[Depends(verify_api_key)])
async def list_models(request: Request):
    return await proxy_request("GET", "/v1/models", request)


@app.get("/v1/models/{model_id}", dependencies=[Depends(verify_api_key)])
async def get_model(model_id: str, request: Request):
    return await proxy_request("GET", f"/v1/models/{model_id}", request)


@app.post("/v1/images/generations", dependencies=[Depends(verify_api_key)])
async def create_image(request: Request, body: Optional[dict] = None):
    return await proxy_request("POST", "/v1/images/generations", request, body)


@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def create_chat(request: Request, body: Optional[dict] = None):
    return await proxy_request("POST", "/v1/chat/completions", request, body)


@app.get("/v1/served_models", dependencies=[Depends(verify_api_key)])
async def list_served_models(request: Request):
    return await proxy_request("GET", "/v1/served_models", request)


@app.post("/v1/tokenize", dependencies=[Depends(verify_api_key)])
async def tokenize(request: Request, body: Optional[dict] = None):
    return await proxy_request("POST", "/v1/tokenize", request, body)


@app.post("/v1/fill", dependencies=[Depends(verify_api_key)])
async def create_fill(request: Request, body: Optional[dict] = None):
    return await proxy_request("POST", "/v1/fill", request, body)
