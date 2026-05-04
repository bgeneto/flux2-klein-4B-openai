ARG CUDA_VERSION=12.6.3
ARG UBUNTU_VERSION=24.04
ARG SD_CPP_REF=master

FROM nvidia/cuda:${CUDA_VERSION}-cudnn-devel-ubuntu${UBUNTU_VERSION} AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    ccache \
    cmake \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src

RUN git clone --recursive https://github.com/leejet/stable-diffusion.cpp.git . \
    && git checkout ${SD_CPP_REF} \
    && git submodule update --init --recursive

RUN cmake . -B ./build -DSD_CUDA=ON -DCMAKE_BUILD_TYPE=Release
RUN cmake --build ./build --config Release -j"$(nproc)"

FROM nvidia/cuda:${CUDA_VERSION}-cudnn-runtime-ubuntu${UBUNTU_VERSION} AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    libgomp1 \
    tini \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

COPY --from=build /src/build/bin/sd-cli /usr/local/bin/sd-cli

COPY app /app/app

RUN mkdir -p /data/outputs

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]