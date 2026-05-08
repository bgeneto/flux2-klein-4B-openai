# Z-Image Turbo Docker Setup

**User:** bgeneto  
**Created:** 5/6/2026 15:24:19  
**Updated:** 5/8/2026 16:54:10  
**Exported:** 5/8/2026 16:54:38  
**Link:** [https://chatgpt.com/c/69fb874f-fdf4-83e9-987b-1ad433687a1a](https://chatgpt.com/c/69fb874f-fdf4-83e9-987b-1ad433687a1a)  

## Prompt:
5/6/2026, 3:24:14 PM

how do I serve openai-compatible image generation endpoint with model z-image turbo with the fastest (and lowest vRAM) possible using docker? similar way that you've done for flux klein previously

## Response:
5/6/2026, 3:24:19 PM

> **Searching for Z-Image-Turbo API and Docker setup**
>
> [Tongyi-MAI/Z-Image · GitHub](https://github.com/Tongyi-MAI/Z-Image)
> [Tongyi-MAI/Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)
> [Install Locally and Create Stunning AI Art - Z‑Image Turbo Guide](https://zimageturbo.org/z-image-turbo)
> [Z-Image Turbo API: Photorealistic Images in Under 1 Second](https://www.atlascloud.ai/models/z-image/turbo)
> [Do We Know Roughly How Much VRAM Will Be Required ...](https://www.reddit.com/r/StableDiffusion/comments/1pbjofv/do_we_know_roughly_how_much_vram_will_be_required/)
> [Best Z Image Turbo API Pricing & Speed](https://wavespeed.ai/docs/docs-api/wavespeed-ai/z-image-turbo)
> [What is Z-Image Turbo (Z Image)? The Complete Beginner's ...](https://z-image.vip/blog/what-is-z-image-turbo-complete-guide)
> [Supercharging Z‑Image Turbo with OpenVINO](https://medium.com/openvino-toolkit/from-text-to-stunning-visuals-supercharging-z-image-turbo-with-openvino-c3585ca9e192)
> [How to Install Z-Image Turbo Locally](https://dev.to/hugh1st/how-to-install-z-image-turbo-locally-4aa8)
> [Z-Image-Turbo ComfyUI Workflow Example](https://docs.comfy.org/tutorials/image/z-image/z-image-turbo)
> [Z-Image Turbo - Fast AI Image Generation](https://sonukumar2.github.io/z-image-turbo/)
>
> **Browsing official documentation for HF/diffusers and GitHub**
>
> [GitHub - Tongyi-MAI/Z-Image · GitHub](https://github.com/Tongyi-MAI/Z-Image)
> [Tongyi-MAI/Z-Image-Turbo · Hugging Face](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)
> [Z-Image-Turbo ComfyUI Workflow Example - ComfyUI](https://docs.comfy.org/tutorials/image/z-image/z-image-turbo)
>
> **Considering Dockerfile for FastAPI and diffusers setup**
>
> I need to figure out the best way to set up a custom Dockerfile with FastAPI and diffusers, aiming for a FastAPI-compatible image endpoint. I’ll also make it efficient, using the Z-Image Turbo for low VRAM usage, and investigate the right diffusers pipeline arguments and versions. I'll look for T2I docs.
>
> **Investigating Dockerfile for FastAPI and Diffusers**
>
> [Z-Image · Hugging Face](https://huggingface.co/docs/diffusers/en/api/pipelines/z_image)
> [GitHub - Tongyi-MAI/Z-Image · GitHub](https://github.com/Tongyi-MAI/Z-Image)
>
> **Reviewing Aquiles support for Z-Image and alternatives**
>
> I’m wondering if Aquiles supports Z-Image’s auto pipeline, since it says it works with HuggingFace’s AutoPipelineForText2Image, but I’m not sure if ZImagePipeline fits that. I can try testing. Also, it might be better to use a custom API, and I should check out SGLang diffusion as another potential option.
>
> **Searching compatibility of Aquiles, Z-Image, and SGLang**
>
> [SGLang Diffusion OpenAI API](https://sgl-project.github.io/diffusion/api/openai_api.html)
> [SGLang is a high-performance serving framework ... - GitHub](https://github.com/sgl-project/sglang)
> [SGLang Diffusion: Accelerating Video and Image Generation](https://lmsys.org/blog/2025-11-07-sglang-diffusion/)
> [Welcome to SGLang - SGLang Documentation](https://docs.sglang.ai/)
> [SGLang: Efficient Execution of Structured Language Model ...](https://arxiv.org/abs/2312.07104)
> [SGLang](https://en.wikipedia.org/wiki/SGLang)
> [OpenAI Compatible API - SGLang](https://sgl-project-sglang-93.mintlify.app/backend/openai-compatible-api)
> [SGLang for Inference | DGX Spark](https://build.nvidia.com/spark/sglang)
> [SGLang diffusion now supports Tongyi Lab's Z-image, an ...](https://www.linkedin.com/posts/sgl-project_sglang-diffusion-now-supports-tongyi-labs-activity-7400391274798964736-BNte)
> [SGLang - Qwen](https://qwen.readthedocs.io/en/latest/deployment/sglang.html)
> [TwinFlow-Z-Image-Turbo-exp/README.md](https://huggingface.co/inclusionAI/TwinFlow-Z-Image-Turbo/blob/main/TwinFlow-Z-Image-Turbo-exp/README.md)
> [sglang-router](https://pypi.org/project/sglang-router/)
>
> **Investigating SGLang diffusion API**
>
> I need to look into how I can open or serve the SGLang diffusion API. This might involve figuring out its setup and hosting options. I'll explore the best way to integrate it or verify whether it requires additional preparation to begin using it effectively.
>
> **Searching for open SGLang diffusion API/serve options**
>
> [SGLang Diffusion — SGLang](https://sgl-project.github.io/diffusion/index.html)
>
> **Looking into installing SGLang**
>
> I need to check how to install or set up SGLang
>
> **Searching installation options for SGLang and Docker**
>
>
> **Adjusting how to trigger actions**
>
> I need to use a click action instead of opening by ID. It seems like this would be more appropriate for the task at hand. I'll adjust my approach so that it triggers the desired action by clicking, rather than directly opening using an ID.
>
> **Exploring click behavior for "not open id"**
>
> [Install SGLang-Diffusion — SGLang](https://sgl-project.github.io/diffusion/installation.html)
>
> **Adjusting image matrix for Z-Image**
>
> I need to add more lines around the image matrix in Z-Image. It seems necessary to refine the borders or provide clearer structure. I'll focus on enhancing this aspect to improve its clarity and responsiveness, making sure it fits with the overall setup.
>
> **Adding lines to z-image matrix boundaries**
>
> [Compatibility Matrix — SGLang](https://sgl-project.github.io/diffusion/compatibility_matrix.html)
>
> **Considering quantization and page lines options**
>
> I’m thinking about adding some quantization page lines, possibly even using a nunchaku technique for clarity or organization. I’ll need to search for approaches or references that can guide this. I want it to be more structured, so I’ll explore how best to incorporate this.
>
> **Searching for quantization and nunchaku references**
>
> [Quantization — SGLang](https://sgl-project.github.io/diffusion/quantization.html)
>
> **Looking into Nunchaku installation examples**
>
> I think I need to find more examples on how to install Nunchaku. This will help me understand the setup better and clarify any tricky steps. I'll look for good guides or case studies to see how others have implemented it successfully.
>
> **Searching for Nunchaku installation examples**
>
> [Quantization — SGLang](https://sgl-project.github.io/diffusion/quantization.html)
>
> **Clarifying Dockerfile and API details for image generation**
>
> It seems like the user is asking how to serve an endpoint, so maybe I should ask if they want Dockerfiles. I can provide a `docker-compose` setup with the SGLang official image and a custom wrapper. I still need to confirm the exact `sglang serve` arguments for image generation, like with Z-Image Turbo and steps like `num_inference_steps`.
>
> **Searching SGLang serve options and OpenAI API docs**
>
> [SGLang Diffusion OpenAI API — SGLang](https://sgl-project.github.io/diffusion/api/openai_api.html)
>
> **Creating a robust Dockerfile for image generation**
>
> I think the answer should suggest using the official SGLang image for best stability. To optimize, I could produce a Dockerfile with the `lmsysorg/sglang:dev` base, installing dependencies during the build instead of at runtime for better performance. The build should include necessary CUDA and VRAM settings. I should also optionally include Nunchaku for lower VRAM use, but it may not always work. I’ll need to find the specific prequantized Z-Image-Turbo checkpoint.
>
> **Searching for Z-Image-Turbo and Nunchaku dependencies**
>
> [svdq-int4_r256-z-image-turbo.safetensors · nunchaku-ai/ ...](https://huggingface.co/nunchaku-ai/nunchaku-z-image-turbo/blob/main/svdq-int4_r256-z-image-turbo.safetensors)
> [Z – Wikipédia, a enciclopédia livre](https://pt.wikipedia.org/wiki/Z)
> [Nunchaku z-image turbo installation guide - ComfyUI](https://www.facebook.com/groups/comfyui/posts/861846636588038/)
> [Onde colocar "Nunchaku svdq-int4-flux.1-dev" ?? : r/comfyui](https://www.reddit.com/r/comfyui/comments/1m8b5vp/where_to_put_nunchaku_svdqint4flux1dev/?tl=pt-br)
> [RuntimeError: string pointer is null in nunchaku ...](https://github.com/nunchaku-ai/nunchaku/issues/861)
> [Studio Z: a sua loja de calçados online e em todo o Brasil](https://www.stz.com.br/?srsltid=AfmBOopVx5HCZaINAaSj6GaZuNntuPBd2OGtCYAHlfjEid_75i6g0d1Y)
> [Sociedade Z](https://www.youtube.com/%40SociedadeZ)
> [Z-Image — Nunchaku 1.3.0 documentation](https://nunchaku.tech/docs/nunchaku/usage/zimage.html)
> [Z | Michaelis On-line - UOL](https://michaelis.uol.com.br/moderno-portugues/busca/portugues-brasileiro/z)
> [Significado de Z ou z no Dicionário Estraviz](https://estraviz.org/Z)
> [多Rank选项兼顾速度与质量，优化扩散模型4位量化推理体验 ...](https://ai.gitcode.com/hf_mirrors/nunchaku-tech/nunchaku-z-image-turbo/blob/main/svdq-int4_r32-z-image-turbo.safetensors)
> [Z](https://en.wikipedia.org/wiki/Z)
> [Letra Z - História Luso-Brasileira](https://historialuso.an.gov.br/glossario/index.php/verbetes-glossario/385-letra-z)
>
> **Clarifying Nunchaku usage with diffusers**
>
> I think I need to clarify how to use Nunchaku with diffusers, though it may not be compatible with SGLang specifically. I'm not totally sure about the details there, so I'll leave it open until I find more information about how Nunchaku fits into the workflow with diffusers.
>
> **Investigating Nunchaku usage with diffusers and alternatives**
>
> [Z-Image — Nunchaku 1.3.0 documentation](https://nunchaku.tech/docs/nunchaku/usage/zimage.html)
> [nunchaku-ai/nunchaku-z-image-turbo · Hugging Face](https://huggingface.co/nunchaku-ai/nunchaku-z-image-turbo)
>
> **Considering Docker Compose for FastAPI with Nunchaku and SGLang**
>
> It seems using Docker Compose might be a good route for a custom FastAPI setup with Nunchaku. However, I'm not sure about directly installing Nunchaku within a container. The idea is to ensure the setup is OpenAI-compatible while minimizing VRAM usage. I’m considering using the correct format for model paths as well
>
> **Browsing Nunchaku installation and Docker Compose compatibility**
>
>
> **Diagnosing function call error with invalid parameters**
>
> [Installation — Nunchaku 1.3.0 documentation](https://nunchaku.tech/docs/nunchaku/installation/installation.html)
>
> **Finalizing the SGLang setup for OpenAI-compatible image server**
>
> I need to recommend using SGLang for an OpenAI-compatible endpoint while maintaining compatibility with Docker, similar to the previous Flux Klein setup. The Docker compose is crucial, and I’ll list the relevant facts: Z-Image Turbo 6B, SGLang’s compatibility, and how Nunchaku works with RTX3090. I should also clarify the VRAM usage and cite all sources.
>
> **Optimizing Dockerfile and server configuration**
>
> I’m considering a potential problem with the `lmsysorg/sglang:dev` image and its work directory. I have to ensure that the repo is properly located in `/sglang`. I’ll add a robust command in the Dockerfile to install dependencies if the source is there. I need to check if the server accepts parameter defaults like `num-inference-steps`.
>
> **Providing Docker options and SGLang command**
>
> There might be a few considerations with whether SGLang API supports guidance/steps, but I can set up defaults for the server. A custom wrapper could offer more control, though combining Nunchaku with OpenAI API might simplify things. Two possible Docker compose profiles could be: `zimage-sglang-int4` and `zimage-diffusers-bf16`. If needed, the Nunchaku + SGLang command could be used to download files and set up the server with specified model paths and configuration.
>
> **Balancing speed and VRAM usage for Nunchaku and SGLang**
>
> For the lowest VRAM usage, I should offload the text encoder to CPU and pin memory, though it will slow down encoding. If speed is the priority, keeping the text encoder on GPU is the way to go. To address these needs, I can provide two Docker profiles: one for speed, using INT4 transformer on GPU, and the other for lowest VRAM, using CPU offload for the text encoder and enabling VAE slicing/tiling.
>
> Thought for 1m 53s

I’ll verify the current serving options for Z-Image-Turbo, then give you a Docker setup optimized for RTX 3090-class VRAM: fastest first, then lowest-VRAM fallback.

I found two viable paths. The cleanest OpenAI-compatible endpoint is SGLang-Diffusion; the lowest-VRAM path is SGLang plus Nunchaku INT4 Z-Image-Turbo weights, especially appropriate for your RTX 3090.

Best current path: **SGLang-Diffusion + Z-Image-Turbo + Nunchaku INT4**. Z-Image-Turbo is a 6B distilled model intended for ~8-step generation and consumer-GPU VRAM, and the official Z-Image example recommends `guidance_scale=0.0` for Turbo models. ([GitHub](https://github.com/Tongyi-MAI/Z-Image)) SGLang-Diffusion provides an OpenAI-compatible `/v1/images/generations` API and explicitly supports Z-Image / Z-Image-Turbo. ([SGLang](https://sgl-project.github.io/diffusion/index.html))

For your RTX 3090, use **INT4**, not NVFP4. Nunchaku’s Z-Image-Turbo repo says INT4 is for pre-50-series GPUs and `r32` is the fastest rank; Nunchaku also lists RTX 3090 / SM86 as supported. ([Hugging Face](https://huggingface.co/nunchaku-ai/nunchaku-z-image-turbo))

## 1. Files

Create this folder:

```bash
mkdir -p zimage-turbo-server
cd zimage-turbo-server
```

### `Dockerfile`

```dockerfile
FROM lmsysorg/sglang:dev

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/cache/huggingface \
    TRANSFORMERS_CACHE=/cache/huggingface \
    HF_HUB_ENABLE_HF_TRANSFER=1

# SGLang dev image usually contains /sglang/python.
# Fallback installs released prerelease package if the source tree is absent.
RUN python3 -m pip install --upgrade pip uv huggingface_hub hf_transfer && \
    if [ -d /sglang/python ]; then \
      cd /sglang && python3 -m pip install -e "python[diffusion]"; \
    else \
      uv pip install --system "sglang[diffusion]" --prerelease=allow; \
    fi && \
    python3 -m pip install nunchaku

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

### `entrypoint.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-30010}"

MODEL_PATH="${MODEL_PATH:-Tongyi-MAI/Z-Image-Turbo}"

# RTX 3090 / Ampere: use int4.
# r32 = fastest, r128 = better quality/slower, r256 = highest quality/slower.
ZIMAGE_PRECISION="${ZIMAGE_PRECISION:-int4}"
ZIMAGE_RANK="${ZIMAGE_RANK:-32}"

NUM_GPUS="${NUM_GPUS:-1}"
NUM_INFERENCE_STEPS="${NUM_INFERENCE_STEPS:-8}"
GUIDANCE_SCALE="${GUIDANCE_SCALE:-0.0}"

DEFAULT_HEIGHT="${DEFAULT_HEIGHT:-1024}"
DEFAULT_WIDTH="${DEFAULT_WIDTH:-1024}"

DIT_PRECISION="${DIT_PRECISION:-bf16}"
VAE_PRECISION="${VAE_PRECISION:-fp16}"

ZIMAGE_MODE="${ZIMAGE_MODE:-fast}"   # fast | lowvram

WEIGHTS_DIR="${WEIGHTS_DIR:-/weights/nunchaku-z-image-turbo}"
WEIGHTS_FILE="svdq-${ZIMAGE_PRECISION}_r${ZIMAGE_RANK}-z-image-turbo.safetensors"
WEIGHTS_PATH="${WEIGHTS_DIR}/${WEIGHTS_FILE}"

mkdir -p "${WEIGHTS_DIR}"

if [ ! -f "${WEIGHTS_PATH}" ]; then
  echo "Downloading ${WEIGHTS_FILE}..."
  python3 - <<PY
import os
from huggingface_hub import hf_hub_download

hf_hub_download(
    repo_id="nunchaku-ai/nunchaku-z-image-turbo",
    filename="${WEIGHTS_FILE}",
    local_dir="${WEIGHTS_DIR}",
    token=os.environ.get("HF_TOKEN") or None,
)
PY
fi

EXTRA_ARGS=()

# Lowest VRAM profile: slower prompt encoding / decoding, lower peak VRAM.
if [ "${ZIMAGE_MODE}" = "lowvram" ]; then
  EXTRA_ARGS+=(
    --text-encoder-cpu-offload
    --pin-cpu-memory
    --vae-tiling
    --vae-slicing
  )
fi

exec sglang serve \
  --model-path "${MODEL_PATH}" \
  --transformer-weights-path "${WEIGHTS_PATH}" \
  --enable-svdquant \
  --quantization-precision "${ZIMAGE_PRECISION}" \
  --quantization-rank "${ZIMAGE_RANK}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --num-gpus "${NUM_GPUS}" \
  --dit-precision "${DIT_PRECISION}" \
  --vae-precision "${VAE_PRECISION}" \
  --height "${DEFAULT_HEIGHT}" \
  --width "${DEFAULT_WIDTH}" \
  --num-inference-steps "${NUM_INFERENCE_STEPS}" \
  --guidance-scale "${GUIDANCE_SCALE}" \
  "${EXTRA_ARGS[@]}"
```

### `docker-compose.yml`

```yaml
services:
  zimage-turbo:
    build:
      context: .
      dockerfile: Dockerfile
    image: local/zimage-turbo-sglang:latest
    container_name: zimage-turbo
    restart: unless-stopped

    ports:
      - "30010:30010"

    gpus: all
    ipc: host
    shm_size: "32gb"

    environment:
      HF_TOKEN: ${HF_TOKEN:-}
      HF_HOME: /cache/huggingface

      CUDA_VISIBLE_DEVICES: "0"

      MODEL_PATH: Tongyi-MAI/Z-Image-Turbo
      PORT: "30010"
      NUM_GPUS: "1"

      # fast = lower latency; lowvram = text encoder CPU offload + VAE tiling/slicing
      ZIMAGE_MODE: fast

      # RTX 3090: int4. Use rank 32 for fastest, 128 for better quality.
      ZIMAGE_PRECISION: int4
      ZIMAGE_RANK: "32"

      NUM_INFERENCE_STEPS: "8"
      GUIDANCE_SCALE: "0.0"

      DEFAULT_HEIGHT: "1024"
      DEFAULT_WIDTH: "1024"

      DIT_PRECISION: bf16
      VAE_PRECISION: fp16

    volumes:
      - ~/.cache/huggingface:/cache/huggingface
      - ./weights:/weights
```

## 2. Start it

```bash
docker compose build
docker compose up -d
docker logs -f zimage-turbo
```

Check model info:

```bash
curl -s http://localhost:30010/models | jq
```

## 3. Test OpenAI-compatible image generation

```bash
curl -sS http://localhost:30010/v1/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer local" \
  -d '{
    "prompt": "A cinematic photo of a Brazilian churrasco grill, premium lighting, realistic, shallow depth of field",
    "size": "1024x1024",
    "n": 1,
    "response_format": "b64_json"
  }' \
| jq -r '.data[0].b64_json' | base64 -d > out.png
```

Python client:

```python
import base64
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:30010/v1",
    api_key="local",
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

## 4. Tuning for your RTX 3090

For **fastest latency**, keep:

```yaml
ZIMAGE_MODE: fast
ZIMAGE_RANK: "32"
NUM_INFERENCE_STEPS: "8"
GUIDANCE_SCALE: "0.0"
DEFAULT_HEIGHT: "1024"
DEFAULT_WIDTH: "1024"
```

For **lowest VRAM**, change:

```yaml
ZIMAGE_MODE: lowvram
DEFAULT_HEIGHT: "768"
DEFAULT_WIDTH: "768"
```

For **better quality but slower**, change:

```yaml
ZIMAGE_RANK: "128"
```

Use `r256` only if you care more about quality than latency. The Nunchaku model card describes `r32` as faster, `r128` as better quality but slower, and `r256` as highest quality but slowest. ([Hugging Face](https://huggingface.co/nunchaku-ai/nunchaku-z-image-turbo))

## Important caveat

If `pip install nunchaku` fails inside the SGLang image, it is usually a PyTorch/CUDA wheel compatibility issue. Nunchaku’s install docs say the wheel must match the Python/PyTorch/CUDA environment; for Linux, Nunchaku requires CUDA ≥ 12.2 and supports SM86 / RTX 3090. ([Nunchaku AI](https://nunchaku.tech/docs/nunchaku/installation/installation.html)) In that case, check the container’s versions:

```bash
docker run --rm --gpus all local/zimage-turbo-sglang:latest \
  python3 - <<'PY'
import sys, torch
print(sys.version)
print(torch.__version__)
print(torch.version.cuda)
print(torch.cuda.get_device_name(0))
PY
```

Then install the matching Nunchaku wheel from their releases instead of the plain `pip install nunchaku`.

---

**Sources:**

- [GitHub - Tongyi-MAI/Z-Image · GitHub](https://github.com/Tongyi-MAI/Z-Image)
- [SGLang Diffusion — SGLang](https://sgl-project.github.io/diffusion/index.html)
- [nunchaku-ai/nunchaku-z-image-turbo · Hugging Face](https://huggingface.co/nunchaku-ai/nunchaku-z-image-turbo)
- [Installation — Nunchaku 1.3.0 documentation](https://nunchaku.tech/docs/nunchaku/installation/installation.html)



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)