from fastapi import FastAPI
from app.core.config import settings
from app.api.endpoints import router
from app.core.database import Base, engine
from dotenv import load_dotenv

load_dotenv()

# Crea las tablas en SQLite si no existen todavía (no borra datos existentes)
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)
app.include_router(router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok"}