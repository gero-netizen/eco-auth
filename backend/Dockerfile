# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

# Dependências de sistema necessárias para compilar pacotes Python nativos
# (cryptography, psycopg) e para o cliente RouterOS.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia primeiro só o que descreve as dependências, para o Docker
# reaproveitar essa camada em builds futuros quando só o código mudar.
COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Usuário não-root — evita rodar o processo do servidor como root dentro
# do contêiner, reduzindo o dano possível em caso de falha de segurança.
RUN useradd --create-home --uid 1000 ecoauth
USER ecoauth

EXPOSE 8000

# /app/data é o volume onde ficam uploads de evidência (fotos/assinatura)
# quando o banco é SQLite local; ao usar PostgreSQL, o banco em si vive
# fora do contêiner (serviço separado no docker-compose).
VOLUME ["/app/uploads"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
