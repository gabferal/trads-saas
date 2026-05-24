# ─────────────────────────────────────────────────
# Stage 1: Build deps em imagem slim
# ─────────────────────────────────────────────────
FROM python:3.12-slim AS base

# Evita geração de .pyc e buffering no stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências de sistema (psycopg2 precisa de libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python primeiro (camada cacheável)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─────────────────────────────────────────────────
# Stage 2: Runtime
# ─────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Apenas biblioteca de runtime do postgres
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copia pacotes instalados do stage anterior
COPY --from=base /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copia código da aplicação
COPY app/          ./app/
COPY frontend/     ./frontend/
COPY alembic/      ./alembic/
COPY alembic.ini   ./alembic.ini
COPY seed.py       ./seed.py

# Cria usuário não-root por segurança
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Usa uvicorn com múltiplos workers em produção
# --workers 1 para evitar problemas de estado em instâncias únicas (Fly.io free tier)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
