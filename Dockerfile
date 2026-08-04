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

# alembic upgrade head corre en cada arranque del contenedor -- es la unica
# fuente de verdad del schema (main.py ya no llama a create_all(), ver
# TECH_DEBT.md #7). Sin esto, un deploy nuevo levantaria con la DB vacia.
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000