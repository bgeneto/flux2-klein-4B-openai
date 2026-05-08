# Z-Image Turbo Stable Diffusion API

OpenAI-compatible image generation API powered by
[stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp), Z-Image
Turbo GGUF weights, Qwen3-4B text encoder weights, and a persistent upstream
`sd-server` backend managed by FastAPI.

This folder is a self-contained Z-Image Turbo copy of the parent project. The
defaults follow [How to Use Z-Image on a GPU with Only 4GB VRAM.md](How%20to%20Use%20Z%E2%80%90Image%20on%20a%20GPU%20with%20Only%204GB%20VRAM.md):

- diffusion model: `z_image_turbo-Q4_K.gguf`
- VAE: `ae.safetensors`
- LLM/text encoder: `Qwen3-4B-Instruct-2507-Q4_K_M.gguf`
- low-VRAM flags enabled by default: `--offload-to-cpu` and `--diffusion-fa`
- optional low-VRAM flags exposed through env vars: `--vae-conv-direct`,
  `--vae-tiling`, and `--clip-on-cpu`

## Features

- OpenAI-compatible `/v1/images/generations` endpoint
- Persistent internal `sd-server`, so model weights stay loaded after startup
- Async job queue with `/v1/jobs/{job_id}` polling
- Bearer token authentication
- Prometheus metrics on `/metrics`
- Generated image serving under `/files/`
- Docker Compose GPU runtime configuration

## Project Structure

```text
.
├── app/
│   └── main.py
├── data/
│   └── .gitkeep
├── models/
│   └── .gitkeep
├── compose.yaml
├── Dockerfile
├── requirements.txt
├── .env.example
├── open-webui-pipe-function.py
└── How to Use Z‐Image on a GPU with Only 4GB VRAM.md
```

## Prerequisites

- NVIDIA GPU with CUDA support
- Docker 20.10+
- Docker Compose v2+
- NVIDIA Container Toolkit

## Quick Start

```bash
cd z-image-turbo
cp .env.example .env
```

Place the model files in `models/`:

```text
models/z_image_turbo-Q4_K.gguf
models/ae.safetensors
models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf
```

You already have `z_image_turbo-Q4_K.gguf`, so the additional files to download
are:

| File | Use | Source |
|---|---|---|
| `ae.safetensors` | VAE passed to `sd-server --vae`. Use this instead of the Flux.2 Klein `flux2-vae.safetensors` default. | <https://huggingface.co/black-forest-labs/FLUX.1-schnell/blob/main/ae.safetensors> |
| `Qwen3-4B-Instruct-2507-Q4_K_M.gguf` | Qwen3 4B text encoder / LLM passed to `sd-server --llm`. Use this instead of the Flux.2 Klein `Qwen3-4B-UD-Q4_K_XL.gguf` file. | <https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/blob/main/Qwen3-4B-Instruct-2507-Q4_K_M.gguf> |

Optional lower-memory LLM alternative:

- If system RAM or startup time is tight, you can choose a smaller file from the
  same Unsloth repository, such as `Qwen3-4B-Instruct-2507-Q3_K_M.gguf`, then set
  `LLM_PATH` in `.env` to that filename. The documented 4GB VRAM example uses
  `Qwen3-4B-Instruct-2507-Q4_K_M.gguf`, so that remains the default here.

Download examples:

```bash
cd z-image-turbo/models

# You already have this file. Put it here with exactly this name:
# z_image_turbo-Q4_K.gguf

# VAE. The FLUX.1-schnell repository may require accepting the Hugging Face terms first.
curl -L -o ae.safetensors \
  "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/ae.safetensors?download=true"

# Qwen3 4B LLM/text encoder.
curl -L -o Qwen3-4B-Instruct-2507-Q4_K_M.gguf \
  "https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen3-4B-Instruct-2507-Q4_K_M.gguf?download=true"
```

After the downloads, `models/` should contain exactly these required runtime
assets:

```text
models/
├── z_image_turbo-Q4_K.gguf
├── ae.safetensors
└── Qwen3-4B-Instruct-2507-Q4_K_M.gguf
```

Then build and run:

```bash
docker compose up --build
```

The API is published on `http://localhost:8006` by default.

## Configuration

| Variable | Description | Default |
|---|---|---|
| `API_KEY` | Bearer token. Set empty to disable auth. | `sk-local` |
| `MODEL_ID` | OpenAI-compatible model id. | `z-image-turbo` |
| `MODEL_PATH` | Z-Image Turbo diffusion GGUF path. | `/models/z_image_turbo-Q4_K.gguf` |
| `VAE_PATH` | VAE path passed to `--vae`. | `/models/ae.safetensors` |
| `TAESD_PATH` | Optional decoder passed to `--taesd` when `VAE_PATH` is empty. | empty |
| `LLM_PATH` | Qwen3-4B GGUF path passed to `--llm`. | `/models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf` |
| `OUTPUT_DIR` | Generated image directory. | `/data/outputs` |
| `PUBLIC_BASE_URL` | External origin for returned `/files/...` URLs. | empty |
| `SD_SERVER_LISTEN_IP` | Internal `sd-server` bind address. | `127.0.0.1` |
| `SD_SERVER_PORT` | Internal `sd-server` port. | `1234` |
| `MAX_CONCURRENT_JOBS` | Wrapper-side generation concurrency. | `1` |
| `QUEUE_MAXSIZE` | Max queued jobs. | `16` |
| `JOB_TIMEOUT_SECONDS` | Per-job timeout. | `180` |
| `DEFAULT_STEPS` | Default sampling steps. | `4` |
| `DEFAULT_CFG_SCALE` | Default CFG scale. | `1.0` |
| `DEFAULT_SAMPLER` | Default sampler. | `euler` |
| `DEFAULT_RNG` | Random number generator. | `cuda` |
| `ENABLE_OFFLOAD_TO_CPU` | Adds `--offload-to-cpu`. Recommended for 4GB VRAM. | `true` |
| `ENABLE_DIFFUSION_FA` | Adds `--diffusion-fa`. Recommended for 4GB VRAM. | `true` |
| `ENABLE_VAE_CONV_DIRECT` | Adds `--vae-conv-direct`. | `false` |
| `ENABLE_VAE_TILING` | Adds `--vae-tiling`. | `false` |
| `ENABLE_CLIP_ON_CPU` | Adds `--clip-on-cpu`. | `false` |
| `ENABLE_MMAP` | Adds `--mmap`. | `false` |
| `DISABLE_IMAGE_METADATA` | Adds `--disable-image-metadata`. | `false` |
| `LOG_LEVEL` | Python logging level. | `INFO` |

Set `ENABLE_VAE_CONV_DIRECT=true`, `ENABLE_VAE_TILING=true`, or
`ENABLE_CLIP_ON_CPU=true` when you need the optional memory-saving behavior
described in the Z-Image 4GB VRAM note.

## Verify

```bash
curl http://localhost:8006/health/live
curl http://localhost:8006/health/ready
curl http://localhost:8006/metrics
```

## Generate An Image

```bash
curl -X POST http://localhost:8006/v1/images/generations \
  -H "Authorization: Bearer sk-local" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "z-image-turbo",
    "prompt": "A cinematic rainy neon metropolis at night",
    "size": "512x1024",
    "steps": 4,
    "cfg_scale": 1.0,
    "n": 1
  }'
```

Use `"response_format": "b64_json"` to receive base64 image data, or keep the
default `"url"` response to receive `/files/...` URLs.

## Async Jobs

Submit asynchronously:

```bash
curl -X POST http://localhost:8006/v1/images/generations \
  -H "Authorization: Bearer sk-local" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A futuristic city at sunset", "async": true}'
```

Poll with:

```bash
curl http://localhost:8006/v1/jobs/<job-id> \
  -H "Authorization: Bearer sk-local"
```

Cancel with:

```bash
curl -X POST http://localhost:8006/v1/jobs/<job-id>/cancel \
  -H "Authorization: Bearer sk-local"
```

## Models Endpoint

```bash
curl http://localhost:8006/v1/models \
  -H "Authorization: Bearer sk-local"
```

returns `z-image-turbo` when the service is configured with the defaults.

## Open WebUI

Import `open-webui-pipe-function.py` into Open WebUI and configure:

```text
IMAGE_API_URL=http://localhost:8006/v1/images/generations
IMAGE_API_KEY=sk-local
MODEL_ID=z-image-turbo
```

## Build Notes

- The Docker image builds `stable-diffusion.cpp` from `master` by default so it
  includes current Z-Image support. Pin `SD_CPP_REF` in `compose.yaml` for
  production reproducibility.
- `.dockerignore` excludes `models/` and `data/`, so local model files and
  generated images are mounted at runtime instead of copied into the image.
- The runtime entrypoint starts FastAPI, and FastAPI starts the internal
  `sd-server` process with the configured model paths and flags.
