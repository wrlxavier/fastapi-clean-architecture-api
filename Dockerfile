FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini README.md ./
COPY alembic ./alembic
COPY app ./app
COPY docker ./docker

RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/app/src \
    PATH=/app/.venv/bin:$PATH

WORKDIR /app

RUN useradd --create-home --shell /bin/sh appuser

COPY --from=builder /app /app

RUN chmod +x /app/docker/api/entrypoint.sh \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["/app/docker/api/entrypoint.sh"]