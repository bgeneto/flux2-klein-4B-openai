# syntax=docker/dockerfile:1.7

FROM lmsysorg/sglang:dev

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/cache/huggingface \
    TRANSFORMERS_CACHE=/cache/huggingface \
    HF_HUB_ENABLE_HF_TRANSFER=1

# SGLang dev image usually contains /sglang.
# Install huggingface_hub, hf_transfer, and nunchaku for Z-Image Turbo support.
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
