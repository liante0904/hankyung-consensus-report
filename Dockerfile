FROM python:3.12-slim-bookworm

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# uv 설치 (pip 사용)
RUN pip install --no-cache-dir uv

# 의존성 설치
COPY uv.lock pyproject.toml ./
RUN uv sync --frozen --no-dev

# 가상환경의 bin 디렉토리를 PATH에 추가
ENV PATH="/app/.venv/bin:$PATH"

# 소스 코드 복사
COPY . .

# 데이터 및 로그를 위한 마운트 포인트 생성
RUN mkdir -p /app/db /app/logs

# 실행
ENTRYPOINT ["python", "app.py"]
