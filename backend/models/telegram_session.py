from datetime import datetime

from sqlalchemy import Column, Integer, BigInteger, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.core.db import Base


#############################################################
# TELEGRAM SESSION STORAGE
# This table stores ONLY Telegram StringSession.
# No user identity, no plan, no analytics fields here.
#############################################################

class TelegramSession(Base):
    __tablename__ = "telegram_sessions"

    id = Column(Integer, primary_key=True)

    # 1-to-1 relationship with users table
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    telegram_id = Column(
        BigInteger,
        unique=True,
        index=True,
        nullable=False,
    )

    session_string = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # ORM relationship back to User
    user = relationship(
        "User",
        back_populates="telegram_session",
        uselist=False,
    )