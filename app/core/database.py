import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# En Railway, DATABASE_URL apunta a un volumen persistente montado
# (ej. sqlite:////data/astrea.db). En local, si no está definida,
# usa el archivo relativo de siempre.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./astrea.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()