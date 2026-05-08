#!/usr/bin/env bash
set -euo pipefail

# ----------------------------
# SGLang configuration
# ----------------------------
SG_LANG_HOST="${SG_LANG_HOST:-0.0.0.0}"
SG_LANG_PORT="${SG_LANG_PORT:-30010}"

MODEL_PATH="${MODEL_PATH:-Tongyi-MAI/Z-Image-Turbo}"

ZIMAGE_PRECISION="${ZIMAGE_PRECISION:-int4}"
ZIMAGE_RANK="${ZIMAGE_RANK:-32}"

NUM_GPUS="${NUM_GPUS:-1}"
NUM_INFERENCE_STEPS="${NUM_INFERENCE_STEPS:-8}"
GUIDANCE_SCALE="${GUIDANCE_SCALE:-0.0}"

DEFAULT_HEIGHT="${DEFAULT_HEIGHT:-1024}"
DEFAULT_WIDTH="${DEFAULT_WIDTH:-1024}"

DIT_PRECISION="${DIT_PRECISION:-bf16}"
VAE_PRECISION="${VAE_PRECISION:-fp16}"

ZIMAGE_MODE="${ZIMAGE_MODE:-fast}"

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

if [ "${ZIMAGE_MODE}" = "lowvram" ]; then
  EXTRA_ARGS+=(
    --text-encoder-cpu-offload
    --pin-cpu-memory
    --vae-tiling
    --vae-slicing
  )
fi

# ----------------------------
# FastAPI configuration
# ----------------------------
FASTAPI_HOST="${FASTAPI_HOST:-0.0.0.0}"
FASTAPI_PORT="${FASTAPI_PORT:-8006}"

# ----------------------------
# Start SGLang in background
# ----------------------------
echo "Starting SGLang on ${SG_LANG_HOST}:${SG_LANG_PORT}..."

sglang serve \
  --model-path "${MODEL_PATH}" \
  --transformer-weights-path "${WEIGHTS_PATH}" \
  --enable-svdquant \
  --quantization-precision "${ZIMAGE_PRECISION}" \
  --quantization-rank "${ZIMAGE_RANK}" \
  --host "${SG_LANG_HOST}" \
  --port "${SG_LANG_PORT}" \
  --num-gpus "${NUM_GPUS}" \
  --dit-precision "${DIT_PRECISION}" \
  --vae-precision "${VAE_PRECISION}" \
  --height "${DEFAULT_HEIGHT}" \
  --width "${DEFAULT_WIDTH}" \
  --num-inference-steps "${NUM_INFERENCE_STEPS}" \
  --guidance-scale "${GUIDANCE_SCALE}" \
  "${EXTRA_ARGS[@]}" &

SG_PID=$!

# Wait for SGLang to be ready
echo "Waiting for SGLang to become ready..."
MAX_RETRIES=60
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if curl -s "http://${SG_LANG_HOST}:${SG_LANG_PORT}/v1/models" > /dev/null 2>&1; then
    echo "SGLang is ready!"
    break
  fi
  RETRY_COUNT=$((RETRY_COUNT + 1))
  echo "  (waiting... attempt ${RETRY_COUNT}/${MAX_RETRIES})"
  sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo "ERROR: SGLang failed to start within ${MAX_RETRIES} retries"
  kill $SG_PID 2>/dev/null || true
  exit 1
fi

# ----------------------------
# Start FastAPI in foreground
# ----------------------------
echo "Starting FastAPI proxy on ${FASTAPI_HOST}:${FASTAPI_PORT}..."

exec uvicorn app.main:app \
  --host "${FASTAPI_HOST}" \
  --port "${FASTAPI_PORT}" \
  --log-level "${LOG_LEVEL:-info}"
