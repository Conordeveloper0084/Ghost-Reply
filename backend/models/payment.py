from datetime import datetime
import enum

from sqlalchemy import Column, Integer, String, Enum as SAEnum, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from backend.core.db import Base

class PaymentStatusEnum(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    canceled = "canceled"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    status = Column(
        SAEnum(PaymentStatusEnum),
        default=PaymentStatusEnum.pending,
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="payments")