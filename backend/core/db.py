from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from .config import settings

# =========================
# Base (ALEMBIC UCHUN MUHIM)
# =========================
class Base(DeclarativeBase):
    pass

# =========================
# Engine
# =========================
engine = create_engine(
    settings.DATABASE_URL,
    echo=False, 
    future=True  # SQLAlchemy 2.0 style
)


# =========================
# Session
# =========================
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


# =========================
# Dependency
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()