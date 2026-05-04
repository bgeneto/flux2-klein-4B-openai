# syntax=docker/dockerfile:1.7

ARG CUDA_VERSION=12.6.3
ARG UBUNTU_VERSION=24.04
ARG SD_CPP_REF=master
ARG APT_MIRROR=https://ubuntu.c3sl.ufpr.br/ubuntu/

FROM nvidia/cuda:${CUDA_VERSION}-cudnn-devel-ubuntu${UBUNTU_VERSION} AS build-base

ARG APT_MIRROR

RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/ubuntu.sources ]; then \
        sed -i "s|http://archive.ubuntu.com/ubuntu/|${APT_MIRROR}|g; s|http://security.ubuntu.com/ubuntu/|${APT_MIRROR}|g" /etc/apt/sources.list.d/ubuntu.sources; \
    fi; \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i "s|http://archive.ubuntu.com/ubuntu/|${APT_MIRROR}|g; s|http://security.ubuntu.com/ubuntu/|${APT_MIRROR}|g" /etc/apt/sources.list; \
    fi

RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository universe \
    && apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ccache \
    cmake \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV CCACHE_DIR=/root/.cache/ccache

WORKDIR /src

FROM build-base AS build

ARG SD_CPP_REF

RUN git clone --recursive --filter=blob:none https://github.com/leejet/stable-diffusion.cpp.git . \
    && git checkout ${SD_CPP_REF} \
    && git submodule update --init --recursive

RUN --mount=type=cache,target=/root/.cache/ccache \
    cmake . -B ./build \
    -DSD_CUDA=ON \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER_LAUNCHER=ccache \
    -DCMAKE_CXX_COMPILER_LAUNCHER=ccache

RUN --mount=type=cache,target=/root/.cache/ccache \
    cmake --build ./build --config Release -j"$(nproc)"

FROM nvidia/cuda:${CUDA_VERSION}-cudnn-runtime-ubuntu${UBUNTU_VERSION} AS runtime-base

ARG APT_MIRROR

RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/ubuntu.sources ]; then \
        sed -i "s|http://archive.ubuntu.com/ubuntu/|${APT_MIRROR}|g; s|http://security.ubuntu.com/ubuntu/|${APT_MIRROR}|g" /etc/apt/sources.list.d/ubuntu.sources; \
    fi; \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i "s|http://archive.ubuntu.com/ubuntu/|${APT_MIRROR}|g; s|http://security.ubuntu.com/ubuntu/|${APT_MIRROR}|g" /etc/apt/sources.list; \
    fi

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    libgomp1 \
    tini \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

FROM runtime-base AS runtime

COPY requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --cache-dir /root/.cache/pip -r /app/requirements.txt

COPY --from=build /src/build/bin/sd-cli /usr/local/bin/sd-cli
COPY --from=build /src/build/bin/sd-server /usr/local/bin/sd-server

COPY app /app/app

RUN mkdir -p /data/outputs

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]