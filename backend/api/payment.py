from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.core.db import get_db
from backend.models.payment import Payment, PaymentStatusEnum
from backend.models.user import User

router = APIRouter(prefix="/payment", tags=["payments"])

PLAN_PRICES = {
    "pro": 21900,
    "premium": 36000,
}

@router.post("/create")
def create_payment(telegram_id: int, plan: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        return {"error": "User not found"}

    payment = Payment(
        user_id=user.id,
        plan=plan,
        amount=PLAN_PRICES[plan]
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {"payment_id": payment.id, "amount": payment.amount}


@router.post("/confirm/{payment_id}")
def confirm_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        return {"error": "Payment not found"}

    payment.status = PaymentStatusEnum.paid
    db.commit()

    # ❌ Hozircha avtomatik upgrade YO'Q
    # user = db.query(User).filter(User.id == payment.user_id).first()
    # user.plan = payment.plan
    # db.commit()

    return {"detail": "Payment confirmed! (But plan not upgraded yet)"} 