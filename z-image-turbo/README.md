# Z-Image Turbo OpenAI-Compatible API

A high-performance, OpenAI-compatible image generation API powered by [SGLang-Diffusion](https://sgl-project.github.io/diffusion), the [Z-Image Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) model, and [Nunchaku INT4](https://github.com/nunchaku-ai/nunchaku-z-image-turbo) quantization for lowest VRAM usage. Built with Docker and GPU acceleration.

## Features

- **OpenAI-compatible API** — Drop-in replacement for the `/v1/images/generations` endpoint
- **GPU-accelerated** — NVIDIA CUDA support via SGLang for fast image generation
- **INT4 Quantization** — Nunchaku svdq-int4 weights for ~4x VRAM reduction with minimal quality loss
- **Low VRAM mode** — CPU offload for text encoder + VAE tiling/slicing for RTX 3090-class GPUs
- **Async generation** — SGLang handles async request processing natively
- **Prometheus metrics** — Built-in observability with `/metrics` endpoint
- **API key authentication** — Bearer token-based security
- **Health checks** — Kubernetes-ready `/health/live` and `/health/ready` endpoints

## Project Structure

```
.
├── app/
│   └── main.py              # FastAPI thin proxy to SGLang backend
├── data/
│   └── .gitkeep             # Placeholder for output directory
├── docker-compose.yml        # Docker Compose configuration
├── Dockerfile                # SGLang + Nunchaku build
├── entrypoint.sh             # Model download and SGLang serve startup
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── .dockerignore
└── .gitignore
```

## Prerequisites

- **NVIDIA GPU** with CUDA support (compute capability 8.6+ recommended for INT4)
  - RTX 3090 (SM86) — supported with INT4
  - RTX 4090 (SM89) — supported with INT4 and NVFP4
- **Docker** (20.10+)
- **Docker Compose** (v2+)
- **NVIDIA Container Toolkit** installed
- **HuggingFace account** with access to Z-Image Turbo weights

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd z-image-turbo

# Copy environment template
cp .env.example .env
```

Edit `.env` to configure your environment. Key settings:

| Variable | Description | Default |
|---|---|---|
| `API_KEY` | Bearer token for authentication | `sk-local` |
| `HF_TOKEN` | HuggingFace token for downloading weights | *(required)* |
| `SGLANG_URL` | SGLang backend URL (internal) | `http://localhost:30010` |
| `ZIMAGE_MODE` | `fast` (lower latency) or `lowvram` (CPU offload) | `fast` |
| `ZIMAGE_PRECISION` | Nunchaku quantization precision | `int4` |
| `ZIMAGE_RANK` | INT4 rank: `32` (fastest), `128` (better quality), `256` (highest quality) | `32` |
| `NUM_INFERENCE_STEPS` | Number of diffusion steps (Z-Image Turbo optimized for ~8) | `8` |
| `GUIDANCE_SCALE` | Guidance scale (Z-Image Turbo uses `0.0`) | `0.0` |
| `DEFAULT_HEIGHT` | Default image height | `1024` |
| `DEFAULT_WIDTH` | Default image width | `1024` |
| `DIT_PRECISION` | Diffusion transformer precision | `bf16` |
| `VAE_PRECISION` | VAE precision | `fp16` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

### 2. Build and Run

```bash
# Build and start with Docker Compose
docker compose up --build

# Or run in detached mode
docker compose up -d --build
```

The first startup will automatically download the Nunchaku INT4 weights from HuggingFace (~3.5GB for svdq-int4_r32).

### 3. Verify

```bash
# Health check
curl http://localhost:30010/health/live

# Ready check (includes SGLang connectivity)
curl http://localhost:30010/health/ready

# Metrics
curl http://localhost:30010/metrics
```

## API Reference

### Authentication

Include the API key as a Bearer token in the `Authorization` header:

```
Authorization: Bearer sk-local
```

### Generate Image

```
POST /v1/images/generations
```

**Request Body:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `prompt` | string | Yes | Text prompt for image generation |
| `negative_prompt` | string | No | Things to exclude from the image |
| `n` | integer | No | Number of images (1-8) |
| `size` | string | No | Image size (e.g., `1024x1024`) |
| `response_format` | string | No | `url` or `b64_json` |
| `steps` | integer | No | Sampling steps (overrides default) |
| `seed` | integer | No | Random seed (-1 for random) |

**Example:**

```bash
curl -X POST http://localhost:30010/v1/images/generations \
  -H "Authorization: Bearer sk-local" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A cinematic photo of a Brazilian churrasco grill, premium lighting, realistic, shallow depth of field",
    "size": "1024x1024",
    "n": 1,
    "response_format": "b64_json"
  }' \
  -o response.json

# Extract image from response
cat response.json | jq -r '.data[0].b64_json' | base64 -d > out.png
```

**Python client:**

```python
import base64
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:30010/v1",
    api_key="sk-local",
)

img = client.images.generate(
    prompt="A cinematic photo of a Brazilian churrasco grill, premium lighting, realistic",
    size="1024x1024",
    n=1,
    response_format="b64_json",
)

with open("out.png", "wb") as f:
    f.write(base64.b64decode(img.data[0].b64_json))
```

### List Models

```
GET /v1/models
```

**Response:**

```json
{
  "object": "list",
  "data": [
    {
      "id": "Tongyi-MAI/Z-Image-Turbo",
      "object": "model",
      "created": 1714867200,
      "owned_by": "local"
    }
  ]
}
```

### Health Checks

```bash
# Liveness probe
curl http://localhost:30010/health/live

# Readiness probe (checks SGLang backend)
curl http://localhost:30010/health/ready
```

### Metrics

Prometheus metrics are available at `/metrics`:

```bash
curl http://localhost:30010/metrics
```

Available metrics:

| Metric | Type | Description |
|---|---|---|
| `zimage_api_requests_total` | Counter | Total API requests by endpoint, method, status |

## Configuration

### Environment Variables

All configuration is managed via environment variables. Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

### Docker Compose Overrides

For local development, create `compose.override.yaml`:

```yaml
services:
  zimage-turbo:
    environment:
      - LOG_LEVEL=DEBUG
```

## Tuning for RTX 3090

### Fastest Latency

```yaml
ZIMAGE_MODE: fast
ZIMAGE_RANK: "32"
NUM_INFERENCE_STEPS: "8"
GUIDANCE_SCALE: "0.0"
DEFAULT_HEIGHT: "1024"
DEFAULT_WIDTH: "1024"
```

### Lowest VRAM

```yaml
ZIMAGE_MODE: lowvram
DEFAULT_HEIGHT: "768"
DEFAULT_WIDTH: "768"
```

### Better Quality (Slower)

```yaml
ZIMAGE_RANK: "128"
```

Use `r256` only if you care more about quality than latency. The Nunchaku model card describes `r32` as fastest, `r128` as better quality but slower, and `r256` as highest quality but slowest.

## Architecture

### Request Flow

```
┌──────────┐     ┌──────────────┐     ┌──────────────────┐
│  Client  │────▶│  FastAPI     │────▶│  SGLang Backend  │
│          │     │  (Proxy)     │     │  (sglang serve)  │
└──────────┘     └──────────────┘     └──────────────────┘
                         │                       │
                         │                       ├──▶ Nunchaku INT4 Weights
                         │                       └──▶ Z-Image Turbo Model
```

1. **Request** arrives at `/v1/images/generations`
2. **Authentication** is verified via API key
3. **Proxy** forwards request to SGLang backend
4. **SGLang** generates image using Z-Image Turbo + Nunchaku INT4
5. **Response** is returned to client (URL or base64)

### Components

- **`verify_api_key`** — Dependency for authentication
- **`metrics_middleware`** — Prometheus metrics collection
- **`proxy_request()`** — Generic request forwarder to SGLang backend

## Troubleshooting

### Common Issues

1. **Missing HF_TOKEN**: You must provide a valid HuggingFace token to download Z-Image Turbo weights
2. **CUDA errors**: Verify NVIDIA Container Toolkit is installed and the GPU is accessible
3. **Nunchaku install fails**: Check container's PyTorch/CUDA versions match Nunchaku requirements (CUDA ≥ 12.2)
4. **Port conflict**: Ensure port 30010 is available

### Debug Mode

Set `LOG_LEVEL=DEBUG` in `.env` for verbose logging.

### Checking Logs

```bash
docker compose logs -f zimage-turbo
```

### Nunchaku Compatibility Check

If `pip install nunchaku` fails inside the container, check versions:

```bash
docker run --rm --gpus all local/zimage-turbo-sglang:latest \
  python3 - <<'PY'
import sys, torch
print(f"Python: {sys.version}")
print(f"PyTorch: {torch.__version__}")
print(f"CUDA: {torch.version.cuda}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
PY
```

Then install the matching Nunchaku wheel from their [releases page](https://github.com/nunchaku-ai/nunchaku/releases).

## References

- [GitHub - Tongyi-MAI/Z-Image](https://github.com/Tongyi-MAI/Z-Image)
- [HuggingFace - Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)
- [SGLang Diffusion Documentation](https://sgl-project.github.io/diffusion/)
- [Nunchaku Z-Image Turbo Weights](https://huggingface.co/nunchaku-ai/nunchaku-z-image-turbo)
- [Nunchaku Installation Guide](https://nunchaku.tech/docs/nunchaku/installation/installation.html)
