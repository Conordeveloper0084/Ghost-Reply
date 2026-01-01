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
    future=True,  # SQLAlchemy 2.0 style

    # 🔥 MUHIM: Railway Postgres + SSL barqarorligi uchun
    pool_size=5,          # nechta doimiy connection
    max_overflow=10,       # vaqtinchalik qo‘shimcha connection
    pool_pre_ping=True,   # o‘lik connection’ni avtomatik tekshiradi
    pool_recycle=300,     # 5 daqiqada connection’ni yangilaydi
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