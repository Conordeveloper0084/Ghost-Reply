from datetime import datetime

from sqlalchemy import Column, Integer, BigInteger, DateTime, Boolean
from backend.core.db import Base


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)

    # Telegram ID of admin
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)

    # Whether admin is active (soft disable possibility)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Admin telegram_id={self.telegram_id} active={self.is_active}>"
