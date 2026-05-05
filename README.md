# FLUX.2-klein Stable Diffusion API

A high-performance, OpenAI-compatible image generation API powered by [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp), the FLUX.2-klein model, and a persistent upstream `sd-server` backend managed by FastAPI. Built with Docker and GPU acceleration.

## Features

- **OpenAI-compatible API** — Drop-in replacement for the `/v1/images/generations` endpoint
- **GPU-accelerated** — NVIDIA CUDA support for fast image generation
- **Persistent backend** — FastAPI starts one internal `sd-server` process and keeps model weights resident after startup
- **Async job queue** — Non-blocking image generation with configurable wrapper-side concurrency
- **Prometheus metrics** — Built-in observability with `/metrics` endpoint
- **API key authentication** — Bearer token-based security
- **Health checks** — Kubernetes-ready `/health/live` and `/health/ready` endpoints
- **Image serving** — Static file serving for generated images at `/files/`
- **Async mode** — Submit jobs and poll for results via `/v1/jobs/{job_id}`

## Project Structure

```
.
├── app/
│   └── main.py              # FastAPI wrapper, sd-server manager, job manager, and API routes
├── data/
│   └── .gitkeep             # Placeholder for output directory
├── models/
│   └── .gitkeep             # Placeholder for model files
├── compose.yaml             # Docker Compose configuration
├── Dockerfile               # Multi-stage Docker build
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
└── .gitignore
```

## Prerequisites

- **NVIDIA GPU** with CUDA support (compute capability 7.0+)
- **Docker** (20.10+)
- **Docker Compose** (v2+)
- **NVIDIA Container Toolkit** installed

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd flux-klein-openai

# Copy environment template
cp .env.example .env
```

Edit `.env` to configure your environment. Key settings:

| Variable | Description | Default |
|---|---|---|
| `API_KEY` | Bearer token for authentication | `sk-local` |
| `MODEL_ID` | Model identifier | `flux-klein-4b` |
| `MODEL_PATH` | Path to the FLUX.2-klein diffusion GGUF file | `/models/flux-2-klein-4b-Q4_0.gguf` |
| `VAE_PATH` | Path to the full Flux.2 VAE used through `--vae` | `/models/flux2-vae.safetensors` |
| `TAESD_PATH` | Optional path to a compatible tiny decoder used through `--taesd` | empty |
| `LLM_PATH` | Path to the Qwen3 4B GGUF file | `/models/Qwen3-4B-UD-Q4_K_XL.gguf` |
| `OUTPUT_DIR` | Directory for generated images | `/data/outputs` |
| `PUBLIC_BASE_URL` | External origin for generated `/files/...` URLs when behind a reverse proxy | empty |
| `SD_SERVER_LISTEN_IP` | Internal bind address for the managed `sd-server` | `127.0.0.1` |
| `SD_SERVER_PORT` | Internal port for the managed `sd-server` | `1234` |
| `SD_SERVER_START_TIMEOUT_SECONDS` | Startup wait time for backend readiness | `120` |
| `SD_SERVER_POLL_INTERVAL_SECONDS` | Poll interval used while waiting on backend jobs | `1.0` |
| `MAX_CONCURRENT_JOBS` | Max parallel generation jobs | `1` |
| `QUEUE_MAXSIZE` | Maximum queue size | `16` |
| `JOB_TIMEOUT_SECONDS` | Job timeout in seconds | `1800` |
| `DEFAULT_STEPS` | Default sampling steps | `4` |
| `DEFAULT_CFG_SCALE` | Classifier-free guidance scale | `1.0` |
| `DEFAULT_SAMPLER` | Sampling method | `euler` |
| `DEFAULT_RNG` | Random number generator | `cuda` |
| `ENABLE_OFFLOAD_TO_CPU` | Enable CPU offloading | `true` |
| `ENABLE_DIFFUSION_FA` | Enable diffusion flash attention | `true` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

Build-time apt mirror override:

| Variable | Description | Default |
|---|---|---|
| `APT_MIRROR` | Ubuntu package mirror used during Docker build | `https://ubuntu.c3sl.ufpr.br/ubuntu/` |

`docker compose` reads `APT_MIRROR` from `.env`, so the normal flow is to keep it in `.env.example`, copy that file to `.env`, and edit the value there as needed.

If you run the API behind a reverse proxy such as Caddy and want generated image URLs to use the public HTTPS origin, set `PUBLIC_BASE_URL` to that external origin, for example `https://imagen.webonly.app`.

These defaults follow the upstream Flux.2 klein documentation for standalone assets:

- FLUX.2-klein 4B diffusion model in GGUF format
- Qwen3 4B text encoder in GGUF format
- FLUX.2 full VAE as the default decoder path
- Optional TAESD only when you have a file that is actually compatible with `--taesd`

The upstream Flux.2 examples use the full VAE through `--vae`. In this workspace, `flux2-vae.safetensors` is the known-good decoder asset. The local `small_decoder.safetensors` file is not enabled by default because it does not match the TAESD tensor layout that upstream `--taesd` expects.

### 2. Place Model Files

Place your model files in the `models/` directory:

```bash
# Example:
# models/flux-2-klein-4b-Q4_0.gguf
# models/Qwen3-4B-UD-Q4_K_XL.gguf
# models/flux2-vae.safetensors
```

Supported alternatives:

- Set `MODEL_PATH=/models/flux-2-klein-base-4b-Q4_K_M.gguf` if you want the base 4B diffusion model instead of klein 4B.
- Leave `TAESD_PATH=` empty to use only the full VAE.
- Set `VAE_PATH=` only if you want to disable the full VAE and rely on a compatible `--taesd` decoder instead.
- If you have the upstream `full_encoder_small_decoder.safetensors` artifact, use it through `VAE_PATH`, not `TAESD_PATH`.
- If your mounted filenames differ from the examples above, only the environment variable values need to change.

### 3. Build and Run

```bash
# Build and start with Docker Compose
docker compose up --build

# Or run in detached mode
docker compose up -d --build

# Or set APT_MIRROR in .env and build normally
docker compose build
```

Build caching notes:

- The Docker build excludes `models/` and `data/` from the build context via `.dockerignore`, so large local assets no longer slow every rebuild.
- Native compilation uses `ccache` and Python dependencies use a persistent `pip` cache through BuildKit cache mounts.
- The expensive `stable-diffusion.cpp` build stage is isolated from application code changes, so editing `app/` should typically only rebuild the final runtime layers.

Runtime note:

- The FastAPI app launches an internal `sd-server` on startup and forwards generation requests to its native async API, so the model stays loaded between requests instead of being reloaded per job.

### 4. Verify

```bash
# Health check
curl http://localhost:8000/health/live

# Ready check (includes model verification)
curl http://localhost:8000/health/ready

# Metrics
curl http://localhost:8000/metrics
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
| `steps` | integer | No | Sampling steps (1-100) |
| `cfg_scale` | float | No | Classifier-free guidance scale (0-50) |
| `sampling_method` | string | No | Sampler: `euler`, `euler_a`, `ddim`, etc. |
| `seed` | integer | No | Random seed (-1 for random) |
| `async` | boolean | No | Return immediately with job ID |

**Example:**

```bash
curl -X POST http://localhost:8000/v1/images/generations \
  -H "Authorization: Bearer sk-local" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A serene Japanese garden with cherry blossoms",
    "size": "1024x1024",
    "steps": 4,
    "cfg_scale": 1.0,
    "n": 1
  }'
```

**Response:**

```json
{
  "created": 1699000000,
  "data": [
    {
      "url": "https://imagen.webonly.app/files/<job-id>/image_001.png",
      "revised_prompt": "A serene Japanese garden with cherry blossoms"
    }
  ]
}
```

### Async Mode

Submit a job and poll for results:

```bash
# Submit job (returns 202 Accepted)
curl -X POST http://localhost:8000/v1/images/generations \
  -H "Authorization: Bearer sk-local" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A futuristic city at sunset",
    "async": true
  }'

# Response:
# {
#   "id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "queued",
#   "created_at": "2024-01-01T00:00:00+00:00"
# }

# Check job status
curl http://localhost:8000/v1/jobs/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer sk-local"

# Cancel a job
curl -X POST http://localhost:8000/v1/jobs/550e8400-e29b-41d4-a716-446655440000/cancel \
  -H "Authorization: Bearer sk-local"
```

Cancellation note:

- Wrapper-side queued jobs can always be cancelled.
- Once upstream `sd-server` has started generating, cancellation depends on upstream behavior and queued backend jobs can be cancelled, but actively generating backend jobs currently return a conflict instead of being interrupted.

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
      "id": "flux-klein-4b",
      "object": "model",
      "created": 1714867200,
      "owned_by": "local",
      "permission": [],
      "root": "flux-klein-4b",
      "parent": null
    }
  ]
}
```

Single-model lookup is also available:

```
GET /v1/models/flux-klein-4b
```

### Health Checks

```bash
# Liveness probe
curl http://localhost:8000/health/live

# Readiness probe (checks model files and managed sd-server)
curl http://localhost:8000/health/ready
```

### Metrics

Prometheus metrics are available at `/metrics`:

```bash
curl http://localhost:8000/metrics
```

Available metrics:

| Metric | Type | Description |
|---|---|---|
| `flux_api_requests_total` | Counter | Total API requests by endpoint, method, status |
| `flux_api_jobs_total` | Counter | Total jobs by status |
| `flux_api_job_duration_seconds` | Histogram | Image generation job duration |
| `flux_api_queue_depth` | Gauge | Current job queue depth |
| `flux_api_running_jobs` | Gauge | Currently running jobs |

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
  flux-api:
    environment:
      - LOG_LEVEL=DEBUG
      - MAX_CONCURRENT_JOBS=2
```

## Development

### Manual Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Building the Docker Image

```bash
docker build -t flux-api .
```

### Running Locally (without Docker)

```bash
# Set environment variables
export MODEL_PATH=/path/to/model.gguf
export VAE_PATH=/path/to/vae.safetensors
export LLM_PATH=/path/to/qwen3.gguf
export OUTPUT_DIR=./data/outputs

# Run
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

This starts the FastAPI wrapper, which in turn starts the local `sd-server` subprocess automatically.

## Architecture

### Job Pipeline

1. **Request** arrives at `/v1/images/generations`
2. **Authentication** is verified via API key
3. **Job** is created and added to the async queue
4. **Worker** picks up the job and submits it to the internal `sd-server` async API
5. **Backend** generates the image using the already-loaded model context
6. **Wrapper** stores returned images under `/files/` and responds with URLs or base64 data

### Components

- **`SDServerManager`** — Starts, monitors, and stops the persistent upstream `sd-server` process
- **`JobManager`** — Manages the async job queue, workers, and cleanup
- **`ImageGenerationRequest`** — Pydantic model for validating API requests
- **`ImageGenerationResponse`** — Pydantic model for API responses
- **`verify_api_key`** — Dependency for authentication
- **`metrics_middleware`** — Prometheus metrics collection

## Troubleshooting

### Common Issues

1. **Missing model files**: Ensure model files exist at the paths specified in `.env`
2. **CUDA errors**: Verify NVIDIA Container Toolkit is installed and the GPU is accessible
3. **Queue full**: Increase `QUEUE_MAXSIZE` or `MAX_CONCURRENT_JOBS` in `.env`
4. **Job timeout**: Increase `JOB_TIMEOUT_SECONDS` for slower GPUs or larger images

### Debug Mode

Set `LOG_LEVEL=DEBUG` in `.env` for verbose logging.

### Checking Logs

```bash
docker compose logs -f flux-api
```

## License

[Add your license here]

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
