# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# deps (psycopg2, ssl etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
 && rm -rf /var/lib/apt/lists/*

# deps python primeiro (cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# código
COPY . .

# usuário não-root (bom pra produção)
RUN useradd -m appuser
COPY --chown=appuser:appuser requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

COPY --chmod=755 --chown=appuser:appuser docker/entrypoint.sh /app/docker/entrypoint.sh
CMD ["/app/docker/entrypoint.sh"]