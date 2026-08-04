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

# HOTFIX TEMPORAL (incidente de produccion, ver commit): "alembic upgrade
# head" saca el contenedor en crash loop porque el alembic_version real de
# produccion esta desincronizado de su schema real (arrastra una tabla
# creada por el viejo create_all() que Alembic no tiene registrada como
# aplicada). Se saca el paso de migracion del arranque para restaurar el
# servicio ya mismo; se revierte a la version con "alembic upgrade head"
# apenas se corrija el puntero de alembic_version en produccion.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]