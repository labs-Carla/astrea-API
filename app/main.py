import swisseph as swe
import os

swe.set_ephe_path(os.path.join(os.path.dirname(__file__), "..", "ephe"))

from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title=settings.app_name)

@app.get("/health")
def health_check():
    return {"status": "ok"}