# syntax=docker/dockerfile:1.7

# Use the sglang image directly - it already has all SGLang binaries and Python packages.
# We just need to add FastAPI and dependencies on top.
FROM lmsysorg/sglang:dev

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/cache/huggingface \
    TRANSFORMERS_CACHE=/cache/huggingface \
    HF_HUB_ENABLE_HF_TRANSFER=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Install only the additional dependencies not included in the base image.
# The base image already has sglang, torch, transformers, etc.
# --break-system-packages required for Debian-based sglang:dev image.
RUN python3 -m pip install --break-system-packages \
    huggingface_hub hf_transfer \
    nunchaku \
    fastapi uvicorn pydantic pydantic-settings httpx prometheus-client

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt --break-system-packages

COPY app /app/app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/entrypoint.sh"]
