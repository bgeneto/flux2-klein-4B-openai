# syntax=docker/dockerfile:1.7

FROM lmsysorg/sglang:dev AS sglang-base

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/cache/huggingface \
    TRANSFORMERS_CACHE=/cache/huggingface \
    HF_HUB_ENABLE_HF_TRANSFER=1

# Install huggingface_hub, hf_transfer, and nunchaku for Z-Image Turbo support.
RUN python3 -m pip install --upgrade pip uv huggingface_hub hf_transfer && \
    if [ -d /sglang/python ]; then \
      cd /sglang && python3 -m pip install -e "python[diffusion]"; \
    else \
      uv pip install --system "sglang[diffusion]" --prerelease=allow; \
    fi && \
    python3 -m pip install nunchaku

# Runtime image with FastAPI app
FROM python:3.11-slim AS runtime

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/cache/huggingface \
    TRANSFORMERS_CACHE=/cache/huggingface \
    HF_HUB_ENABLE_HF_TRANSFER=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Copy SGLang binaries from sglang-base
COPY --from=sglang-base /usr/local/bin/sglang /usr/local/bin/sglang
COPY --from=sglang-base /usr/local/bin/sgl-router /usr/local/bin/sgl-router
COPY --from=sglang-base /usr/local/bin/sgl-worker /usr/local/bin/sgl-worker
COPY --from=sglang-base /usr/local/bin/sgl-tokenizer /usr/local/bin/sgl-tokenizer
COPY --from=sglang-base /usr/local/bin/sgl-lm-eagereader /usr/local/bin/sgl-lm-eagereader
COPY --from=sglang-base /usr/local/lib/python3.11/site-packages/sglang /usr/local/lib/python3.11/site-packages/sglang
COPY --from=sglang-base /usr/local/lib/python3.11/site-packages/transformers /usr/local/lib/python3.11/site-packages/transformers

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/entrypoint.sh"]
