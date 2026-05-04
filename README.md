# FLUX.2-klein Stable Diffusion API

A high-performance, OpenAI-compatible image generation API powered by [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) and the FLUX.2-klein model. Built with FastAPI, Docker, and GPU acceleration.

## Features

- **OpenAI-compatible API** — Drop-in replacement for the `/v1/images/generations` endpoint
- **GPU-accelerated** — NVIDIA CUDA support for fast image generation
- **Async job queue** — Non-blocking image generation with configurable concurrency
- **Prometheus metrics** — Built-in observability with `/metrics` endpoint
- **API key authentication** — Bearer token-based security
- **Health checks** — Kubernetes-ready `/health/live` and `/health/ready` endpoints
- **Image serving** — Static file serving for generated images at `/files/`
- **Async mode** — Submit jobs and poll for results via `/v1/jobs/{job_id}`

## Project Structure

```
.
├── app/
│   └── main.py              # FastAPI application, job manager, and API routes
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
| `MODEL_PATH` | Path to the GGUF model file | `/models/flux-2-klein-4b-Q4_K_M.gguf` |
| `VAE_PATH` | Path to the VAE file | `/models/flux2_ae.safetensors` |
| `LLM_PATH` | Path to the LLM file | `/models/qwen_3_4b.safetensors` |
| `OUTPUT_DIR` | Directory for generated images | `/data/outputs` |
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

### 2. Place Model Files

Place your model files in the `models/` directory:

```bash
# Example:
# models/flux-2-klein-4b-Q4_K_M.gguf
# models/flux2_ae.safetensors
# models/qwen_3_4b.safetensors
```

### 3. Build and Run

```bash
# Build and start with Docker Compose
docker compose up --build

# Or run in detached mode
docker compose up -d --build
```

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
    "cfg_scale": 7.0,
    "n": 1
  }'
```

**Response:**

```json
{
  "created": 1699000000,
  "data": [
    {
      "url": "http://localhost:8000/files/<job-id>/image_001.png",
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
      "owned_by": "local"
    }
  ]
}
```

### Health Checks

```bash
# Liveness probe
curl http://localhost:8000/health/live

# Readiness probe (checks model files)
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
export LLM_PATH=/path/to/llm.safetensors
export OUTPUT_DIR=./data/outputs

# Run
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Architecture

### Job Pipeline

1. **Request** arrives at `/v1/images/generations`
2. **Authentication** is verified via API key
3. **Job** is created and added to the async queue
4. **Worker** picks up the job and executes `sd-cli` with the appropriate parameters
5. **Result** is returned with URLs to generated images (or base64 data)

### Components

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
