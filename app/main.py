from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter
from app.core.config import settings
from app.api.endpoints import router
from app.core.database import Base, engine
from dotenv import load_dotenv

load_dotenv()

# Crea las tablas en SQLite si no existen todavía (no borra datos existentes)
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

# Registra el limiter (importado de app/core/limiter.py) en el estado de la
# app, y el manejador que convierte un límite excedido en una respuesta 429
# clara en vez de un error genérico.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://astrea-landing-8j2sk0sut-cartapotencials-projects.vercel.app",  # tu preview actual
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok"}