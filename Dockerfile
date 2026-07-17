FROM python:3.11-slim

# Librerías de sistema que WeasyPrint necesita para renderizar PDFs
# (Pango/Cairo/GDK-Pixbuf), sin las cuales el import de pdf_service.py
# falla y tumba toda la aplicación al arrancar.
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]