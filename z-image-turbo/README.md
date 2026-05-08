# Z-Image Turbo Stable Diffusion API

OpenAI-compatible image generation API powered by
[stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp), Z-Image
Turbo GGUF weights, Qwen3-4B text encoder weights, and a persistent upstream
`sd-server` backend managed by FastAPI.

This folder is a self-contained Z-Image Turbo copy of the parent project. The
defaults follow [How to Use Z-Image on a GPU with Only 4GB VRAM.md](How%20to%20Use%20Z%E2%80%90Image%20on%20a%20GPU%20with%20Only%204GB%20VRAM.md):

- diffusion model: `z_image_turbo-Q4_1.gguf`
- VAE / autoencoder: `ae.safetensors`
- LLM/text encoder: `Qwen3-4B-UD-Q4_K_XL.gguf`
- sampling steps: `9`
- CFG scale: `1.0`
- sampler/scheduler: `euler` + `simple`
- RNG: `cpu`
- low-VRAM flag enabled by default: `--offload-to-cpu`
- optional low-VRAM flags exposed through env vars: `--vae-conv-direct`,
  `--vae-tiling`, `--clip-on-cpu`, and `--diffusion-fa`

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
models/z_image_turbo-Q4_1.gguf
models/ae.safetensors
models/Qwen3-4B-UD-Q4_K_XL.gguf
```

You already have `z_image_turbo-Q4_1.gguf`, so the additional files to download
are:

| File | Use | Source |
|---|---|---|
| `ae.safetensors` | Autoencoder/VAE passed to `sd-server --vae`. This is the file used by the PR #1020 `ae.sft` / `ae.safetensors` examples and by ComfyUI Z-Image Turbo workflows. | <https://huggingface.co/black-forest-labs/FLUX.1-schnell/blob/main/ae.safetensors> |
| `Qwen3-4B-UD-Q4_K_XL.gguf` | Qwen3 4B text encoder / LLM passed to `sd-server --llm`. This is the Qwen3 4B GGUF variant used by known-working Z-Image Turbo stable-diffusion.cpp setups. | <https://huggingface.co/unsloth/Qwen3-4B-GGUF/blob/main/Qwen3-4B-UD-Q4_K_XL.gguf> |

About VAE vs AE: `--vae` is the stable-diffusion.cpp command-line option, but
the file it loads for Flux/Z-Image models is often named `ae.safetensors` or
`ae.sft` because it is the autoencoder. For this stable-diffusion.cpp project,
use `ae.safetensors` as the baseline. The official Z-Image Turbo Diffusers repo
also contains `vae/diffusion_pytorch_model.safetensors` (168 MB), and some
people can run it, but the PR #1020 known-good commands and ComfyUI Z-Image
Turbo workflows use `ae.safetensors` / `ae.sft`. Do not use `ae-f16.gguf` while
debugging white images; that is a GGUF conversion and adds another variable.

Optional lower-memory LLM alternative:

- If system RAM or startup time is tight, you can choose a smaller file from the
  same Unsloth `Qwen3-4B-GGUF` repository, then set `LLM_PATH` in `.env` to that
  filename. Keep `Qwen3-4B-UD-Q4_K_XL.gguf` as the baseline while debugging.

Download examples:

```bash
cd z-image-turbo/models

# You already have this file. Put it here with exactly this name:
# z_image_turbo-Q4_1.gguf

# VAE / autoencoder used by stable-diffusion.cpp and ComfyUI Z-Image examples.
# The FLUX.1-schnell repository is gated, so accept its Hugging Face terms first.
curl -L -o ae.safetensors \
  "https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/ae.safetensors?download=true"

# Qwen3 4B LLM/text encoder.
curl -L -o Qwen3-4B-UD-Q4_K_XL.gguf \
  "https://huggingface.co/unsloth/Qwen3-4B-GGUF/resolve/main/Qwen3-4B-UD-Q4_K_XL.gguf?download=true"
```

After the downloads, `models/` should contain exactly these required runtime
assets:

```text
models/
├── z_image_turbo-Q4_1.gguf
├── ae.safetensors
└── Qwen3-4B-UD-Q4_K_XL.gguf
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
| `MODEL_PATH` | Z-Image Turbo diffusion GGUF path. | `/models/z_image_turbo-Q4_1.gguf` |
| `VAE_PATH` | VAE/autoencoder path passed to `--vae`. | `/models/ae.safetensors` |
| `TAESD_PATH` | Optional decoder passed to `--taesd` when `VAE_PATH` is empty. | empty |
| `LLM_PATH` | Qwen3-4B GGUF path passed to `--llm`. | `/models/Qwen3-4B-UD-Q4_K_XL.gguf` |
| `OUTPUT_DIR` | Generated image directory. | `/data/outputs` |
| `PUBLIC_BASE_URL` | External origin for returned `/files/...` URLs. | empty |
| `SD_SERVER_LISTEN_IP` | Internal `sd-server` bind address. | `127.0.0.1` |
| `SD_SERVER_PORT` | Internal `sd-server` port. | `1234` |
| `MAX_CONCURRENT_JOBS` | Wrapper-side generation concurrency. | `1` |
| `QUEUE_MAXSIZE` | Max queued jobs. | `16` |
| `JOB_TIMEOUT_SECONDS` | Per-job timeout. | `180` |
| `DEFAULT_STEPS` | Default sampling steps. Matches leejet's fixed PR #1020 command. | `9` |
| `DEFAULT_CFG_SCALE` | Default CFG scale. | `1.0` |
| `DEFAULT_SAMPLER` | Default sampler. | `euler` |
| `DEFAULT_SCHEDULER` | Default scheduler passed to `--scheduler`. `simple` matches leejet's fixed PR #1020 command. | `simple` |
| `DEFAULT_FLOW_SHIFT` | Optional flow shift passed to `--flow-shift`. Leave empty for the PR #1020 baseline. | empty |
| `DEFAULT_RNG` | Random number generator. `cpu` matches leejet's fixed PR #1020 command and avoids CUDA RNG variance while debugging. | `cpu` |
| `ENABLE_OFFLOAD_TO_CPU` | Adds `--offload-to-cpu`. Recommended for 4GB VRAM. | `true` |
| `ENABLE_DIFFUSION_FA` | Adds `--diffusion-fa`. Keep disabled for the first known-good baseline; re-enable after image output is correct. | `false` |
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

Use `DEFAULT_STEPS=9`, `DEFAULT_SCHEDULER=simple`, and `DEFAULT_RNG=cpu` while
debugging. This matches leejet's fixed PR #1020 command after the Qwen3 rope and
K-quant NaN fixes landed. Z-Image Turbo can run at 8 steps, and other users show
good results at 4-8 steps with other schedulers, but this project now starts
from the clearest upstream known-good baseline.

Keep `DEFAULT_CFG_SCALE=1.0` for this stable-diffusion.cpp setup. The leejet
GGUF example uses `--cfg-scale 1.0`; higher CFG is usually not needed for the
Turbo model and may hurt image quality. If you experiment, change one setting at
a time and compare fixed-seed outputs.

Leave `DEFAULT_FLOW_SHIFT=` empty for the baseline. The working PR commands do
not include `--flow-shift`, so this wrapper should not add it unless you are
running an explicit experiment.

### Sampler And Negative Prompts

`DEFAULT_SAMPLER=euler` is the conservative default for this project. It is
fast, stable, and appears in working stable-diffusion.cpp Z-Image examples.
Other samplers can work:

- `euler` with `simple` is the safest first choice because it matches leejet's
  fixed command in PR #1020.
- `heun` and `dpm2` can produce good results, but stable-diffusion.cpp users
  report that they are slower and often need fewer steps, for example 4-5 steps
  instead of 7-9 Euler steps.
- `smoothstep` and `sgm_uniform` also appear in successful community tests, but
  switch to them only after the baseline produces non-white images.
- If you change sampler, keep `DEFAULT_CFG_SCALE=1.0`, `DEFAULT_RNG=cpu`, and a fixed seed while
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

1. Rebuild stable-diffusion.cpp without Docker cache.

   PR #1020 includes fixes for Qwen3 naming/rope and NaNs with CUDA K-quants.
   Because this Dockerfile clones `stable-diffusion.cpp` inside a cached build
   layer, `docker compose up --build` can keep an older broken binary. Force a
   clean rebuild before chasing model files:

   ```bash
   cd z-image-turbo
   docker compose build --no-cache z-image-api
   docker compose up --force-recreate
   ```

2. Confirm the files are real model files, not failed downloads:

   ```bash
   ls -lh models
   file models/ae.safetensors models/Qwen3-4B-UD-Q4_K_XL.gguf models/z_image_turbo-Q4_1.gguf
   ```

   `ae.safetensors` should be a large binary file, not a small HTML, JSON, or
   text file. The Black Forest Labs repository is gated; a failed unauthenticated
   download can save an error page under the requested filename.

3. Prefer one of the quantizations recommended by the stable-diffusion.cpp
   Z-Image 4GB VRAM wiki if your `z_image_turbo-Q4_1.gguf` keeps producing
   white images:

   ```text
   z_image_turbo-Q4_0.gguf
   z_image_turbo-Q3_K.gguf
   ```

   The wiki recommends `Q4_0` or `Q3_K` for 4GB VRAM. `Q4_K` appears in the
   comparison table and may work for some users, but it is not the listed 4GB
   recommendation.

4. Keep Flash Attention disabled until the baseline works:

   ```bash
   ENABLE_DIFFUSION_FA=false docker compose up --force-recreate
   ```

5. Keep Z-Image-specific sampling defaults while testing:

   ```text
   DEFAULT_STEPS=9
   DEFAULT_CFG_SCALE=1.0
   DEFAULT_SAMPLER=euler
   DEFAULT_SCHEDULER=simple
   DEFAULT_FLOW_SHIFT=
   DEFAULT_RNG=cpu
   ENABLE_OFFLOAD_TO_CPU=true
   ENABLE_DIFFUSION_FA=false
   ```

6. Test the backend directly with `sd-cli` inside the container so you can
   separate stable-diffusion.cpp/model issues from the FastAPI wrapper:

   ```bash
   docker compose run --rm z-image-api sd-cli \
     --diffusion-model /models/z_image_turbo-Q4_1.gguf \
     --vae /models/ae.safetensors \
     --llm /models/Qwen3-4B-UD-Q4_K_XL.gguf \
     --steps 9 \
     --cfg-scale 1.0 \
     --sampling-method euler \
     --scheduler simple \
     --rng cpu \
     --offload-to-cpu \
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
    "steps": 9,
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
