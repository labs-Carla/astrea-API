from fastapi import FastAPI
from app.core.config import settings
from app.api.endpoints import router

app = FastAPI(title=settings.app_name)
app.include_router(router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok"}