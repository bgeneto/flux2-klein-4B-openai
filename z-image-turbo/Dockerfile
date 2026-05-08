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

# Install huggingface_hub, hf_transfer, nunchaku, and FastAPI dependencies.
# --break-system-packages required for Debian-based sglang:dev image.
RUN python3 -m pip install --upgrade pip uv huggingface_hub hf_transfer --break-system-packages && \
    if [ -d /sglang/python ]; then \
      cd /sglang && python3 -m pip install -e "python[diffusion]" --break-system-packages; \
    else \
      uv pip install --system --break-system-packages "sglang[diffusion]" --prerelease=allow; \
    fi && \
    python3 -m pip install nunchaku --break-system-packages && \
    python3 -m pip install --break-system-packages fastapi uvicorn pydantic pydantic-settings httpx prometheus-client && \
    python3 -m pip cache purge

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt --break-system-packages

COPY app /app/app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/entrypoint.sh"]
