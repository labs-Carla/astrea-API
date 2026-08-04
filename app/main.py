from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api.carta_natal import router as carta_natal_router
from app.api.admin import router as admin_router
from app.api.horoscopos import router as horoscopos_router
from app.api.dev_test import router as dev_test_router
from dotenv import load_dotenv

load_dotenv()
setup_logging()

# El schema de la base de datos se gestiona exclusivamente via Alembic
# ("alembic upgrade head", ver CLAUDE.md/README.md) -- ya no se crea
# automaticamente aqui. Antes coexistian create_all() y Alembic sin una
# unica fuente de verdad; ver TECH_DEBT.md #7.
app = FastAPI(title=settings.app_name)

# Registra el limiter (importado de app/core/limiter.py) en el estado de la
# app, y el manejador que convierte un límite excedido en una respuesta 429
# clara en vez de un error genérico.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "https://astrea-charts.site",
    "https://astrea-landing-omega.vercel.app",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "https://astrea-informe-react.vercel.app",
],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sirve archivos estáticos (CSS, JS, imágenes) para la versión web del reporte,
# accesibles en /static/... (ej. /static/css/carta_web.css)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(carta_natal_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(horoscopos_router, prefix="/api/v1")
app.include_router(dev_test_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok"}