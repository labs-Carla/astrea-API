from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Base de datos SQLite como archivo local, simple para MVP.
# El archivo se crea automáticamente en la raíz del proyecto si no existe.
DATABASE_URL = "sqlite:///./astrea.db"

# check_same_thread=False es necesario porque FastAPI puede manejar
# requests en hilos distintos, y SQLite por defecto solo permite acceso
# desde el hilo que abrió la conexión.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency de FastAPI: abre una sesión de base de datos por request,
    y la cierra automáticamente al terminar (incluso si hay un error).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()