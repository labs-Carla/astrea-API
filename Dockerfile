FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Corre como usuario no privilegiado en vez de root -- endurecimiento
# estandar de contenedores (ver TECH_DEBT.md #9). chown despues del COPY
# para que appuser pueda escribir el sqlite local (./astrea.db) si
# DATABASE_URL no apunta a un volumen externo.
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# alembic upgrade head corre en cada arranque del contenedor -- es la unica
# fuente de verdad del schema (main.py ya no llama a create_all(), ver
# TECH_DEBT.md #7). Sin esto, un deploy nuevo levantaria con la DB vacia.
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000