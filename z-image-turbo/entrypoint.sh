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
