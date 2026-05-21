FROM python:3.12-slim

WORKDIR /app/apps/recommender

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.10.8 /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-install-project

COPY . .
RUN uv sync --frozen --no-cache

ENV PYTHONPATH=/app/apps/recommender
ENV OPENBLAS_NUM_THREADS=1

CMD ["uv", "run", "python", "-m", "recommender.train_model"]
