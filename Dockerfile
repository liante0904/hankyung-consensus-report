# 1. Build stage
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# 2. Final stage
FROM python:3.12-slim-bookworm
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# 빌드 결과물 복사
COPY --from=builder /app/.venv /app/.venv
COPY . .

# 데이터 및 로그를 위한 마운트 포인트 생성
RUN mkdir -p /app/db /app/logs

# 실행
ENTRYPOINT ["python", "app.py"]
