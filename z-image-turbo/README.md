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
- sampling steps: `8`
- CFG scale: `1.0`
- sampler/scheduler: `euler` + `smoothstep`
- flow shift: `3.0`
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
| `DEFAULT_STEPS` | Default sampling steps. Z-Image Turbo is distilled for 8 NFE / steps. | `8` |
| `DEFAULT_CFG_SCALE` | Default CFG scale. | `1.0` |
| `DEFAULT_SAMPLER` | Default sampler. | `euler` |
| `DEFAULT_SCHEDULER` | Default scheduler passed to `--scheduler`. `smoothstep` is commonly used with Z-Image in stable-diffusion.cpp. | `smoothstep` |
| `DEFAULT_FLOW_SHIFT` | Flow shift passed to `--flow-shift`. Z-Image discussions note a default of `3.0`. | `3.0` |
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

### Recommended Z-Image Turbo Defaults

Use `DEFAULT_STEPS=8` for normal use. Z-Image Turbo is the distilled variant of
Z-Image and is designed around 8 function evaluations / sampling steps. Four
steps may run faster, but it is below the model's intended operating point and
can reduce prompt adherence, text rendering, and fine detail.

Keep `DEFAULT_CFG_SCALE=1.0` for this stable-diffusion.cpp setup. The leejet
GGUF example uses `--cfg-scale 1.0`; higher CFG is usually not needed for the
Turbo model and may hurt image quality. If you experiment, change one setting at
a time and compare fixed-seed outputs.

For stable-diffusion.cpp specifically, this project also sets
`DEFAULT_SCHEDULER=smoothstep` and `DEFAULT_FLOW_SHIFT=3.0`. Those values match
working Z-Image settings discussed by stable-diffusion.cpp users and avoid
falling back to generic diffusion defaults.

### Sampler And Negative Prompts

`DEFAULT_SAMPLER=euler` is the conservative default for this project. It is
fast, stable, and appears in working stable-diffusion.cpp Z-Image examples.
Other samplers can work:

- `euler` with `smoothstep` is the safest first choice.
- `heun` and `dpm2` can produce good results, but stable-diffusion.cpp users
  report that they are slower and often need fewer steps, for example 4-5 steps
  instead of 7-9 Euler steps.
- If you change sampler, keep `DEFAULT_SCHEDULER=smoothstep`,
  `DEFAULT_FLOW_SHIFT=3.0`, `DEFAULT_CFG_SCALE=1.0`, and a fixed seed while
  comparing.

Negative prompts are not recommended for normal Z-Image Turbo use. The official
Diffusers Z-Image pipeline examples use `guidance_scale=0.0`, and Diffusers
documents that negative prompts are ignored when guidance is not enabled. In
this stable-diffusion.cpp setup, `cfg_scale=1.0` follows the leejet GGUF example,
so negative prompts should be treated as unsupported or at least unreliable for
Turbo. Put restrictions in the positive prompt instead, for example:

```text
a clean product photo on a white table, no text, no watermark, no logo
```

## Troubleshooting White Images

If generation succeeds but the PNG is completely white, check these first:

1. Confirm the files are real model files, not failed downloads:

   ```bash
   ls -lh models
   file models/ae.safetensors models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf models/z_image_turbo-Q4_K.gguf
   ```

   `ae.safetensors` should be a large binary file, not a small HTML, JSON, or
   text file. Hugging Face gated downloads can save an error page under the
   requested filename if you have not accepted the model terms or authenticated.

2. Prefer one of the quantizations recommended by the stable-diffusion.cpp
   Z-Image 4GB VRAM wiki if your `z_image_turbo-Q4_K.gguf` keeps producing
   white images:

   ```text
   z_image_turbo-Q4_0.gguf
   z_image_turbo-Q3_K.gguf
   ```

   The wiki recommends `Q4_0` or `Q3_K` for 4GB VRAM. `Q4_K` appears in the
   comparison table and may work for some users, but it is not the listed 4GB
   recommendation.

3. Try disabling Flash Attention if your GPU/driver/backend has a kernel issue:

   ```bash
   ENABLE_DIFFUSION_FA=false docker compose up --force-recreate
   ```

4. Keep Z-Image-specific sampling defaults while testing:

   ```text
   DEFAULT_STEPS=8
   DEFAULT_CFG_SCALE=1.0
   DEFAULT_SAMPLER=euler
   DEFAULT_SCHEDULER=smoothstep
   DEFAULT_FLOW_SHIFT=3.0
   ```

5. Test the backend directly with `sd-cli` inside the container so you can
   separate stable-diffusion.cpp/model issues from the FastAPI wrapper:

   ```bash
   docker compose run --rm z-image-api sd-cli \
     --diffusion-model /models/z_image_turbo-Q4_K.gguf \
     --vae /models/ae.safetensors \
     --llm /models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf \
     --steps 8 \
     --cfg-scale 1.0 \
     --sampling-method euler \
     --scheduler smoothstep \
     --flow-shift 3.0 \
     --offload-to-cpu \
     --diffusion-fa \
     -H 1024 \
     -W 1024 \
     -p "a detailed photo of a red apple on a wooden table" \
     -o /data/z-image-smoke-test.png
   ```

   If this direct command also produces a white image, the problem is almost
   certainly the model files, quantization, GPU backend, or stable-diffusion.cpp
   build rather than this API wrapper.

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
    "steps": 8,
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
