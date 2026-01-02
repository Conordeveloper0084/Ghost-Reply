from datetime import datetime
import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Enum as SAEnum,
    BigInteger,
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from backend.core.db import Base


class PlanEnum(str, enum.Enum):
    free = "free"
    pro = "pro"
    premium = "premium"


#############################################################
# WARNING: ADMIN / CORE USER DATA ONLY
# This table is for identity, plan, status, trigger counters,
# and relations. DO NOT store Telegram session strings here.
#############################################################

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_session = relationship("TelegramSession", back_populates="user", uselist=False)


    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)

    name = Column(String)

    is_admin = Column(Boolean, default=False, nullable=False)
    
    username = Column(String, nullable=True)
    phone = Column(String, nullable=True)


    language = Column(String, default="uz", nullable=False)

    registered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    worker_id = Column(String, nullable=True, index=True)

    worker_active = Column(Boolean, default=False)
    last_seen_at = Column(DateTime, nullable=True)

    plan = Column(
        SAEnum(PlanEnum, name="plan_enum"),
        default=PlanEnum.free,
        nullable=False
    )
    plan_expires_at = Column(DateTime, nullable=True)

    is_registered = Column(Boolean, default=False)

    trigger_count = Column(Integer, default=0, nullable=False)

    payments = relationship(
        "Payment",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    telegram_session = relationship(
        "TelegramSession",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @hybrid_property
    def is_plan_active(self) -> bool:
        if self.plan_expires_at is None:
            return True
        return self.plan_expires_at > datetime.utcnow()

    @hybrid_property
    def trigger_limit(self) -> int:
        if not self.is_plan_active:
            return 0
        if self.plan == PlanEnum.free:
            return 3
        if self.plan == PlanEnum.pro:
            return 10
        if self.plan == PlanEnum.premium:
            return 20
        return 0

    @hybrid_property
    def can_create_trigger(self) -> bool:
        if not self.worker_active:
            return False
        if not self.is_plan_active:
            return False
        return self.trigger_count < self.trigger_limit