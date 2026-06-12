FROM nvidia/cuda:12.9.1-cudnn-runtime-ubuntu24.04 AS dldn-bench-instanovo-aichor

ENV DEBIAN_FRONTEND=noninteractive
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:/root/.local/bin:${PATH}"
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      git \
      python3.12 \
      python3.12-venv \
      python3-pip && \
    rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

COPY pyproject.toml README.md ./
COPY *.py ./
COPY scripts ./scripts

RUN uv venv "${VIRTUAL_ENV}" --python python3.12 && \
    uv pip install --python "${VIRTUAL_ENV}/bin/python" .

CMD ["bash", "scripts/aichor/run_all.sh"]
