from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.core.db import get_db
from backend.models.user import User
from backend.models.trigger import Trigger

from backend.schemas.trigger import (
    TriggerCreate,
    TriggerRead,
    TriggerUpdate,
)

router = APIRouter(prefix="/triggers", tags=["triggers"])


@router.post("/", response_model=TriggerRead)
def create_trigger(payload: TriggerCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == payload.user_telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.worker_active:
        raise HTTPException(
            status_code=409,
            detail="Worker not active. Reconnect account."
        )

    existing_trigger = db.query(Trigger).filter(
        Trigger.user_id == user.id,
        Trigger.trigger_text == payload.trigger_text.lower()
    ).first()
    if existing_trigger:
        raise HTTPException(
            status_code=409,
            detail="Trigger already exists."
        )

    limit = user.trigger_limit  # free=3, pro=10, premium=20

    if user.trigger_count >= limit:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Trigger limit reached for plan {user.plan.value}. "
                f"Limit = {limit}, Current count = {user.trigger_count}"
            ),
        )

    trigger = Trigger(
        user_id=user.id,
        trigger_text=payload.trigger_text.lower(),
        reply_text=payload.reply_text,
        is_active=True,
    )

    db.add(trigger)
    user.trigger_count += 1
    db.commit()
    db.refresh(trigger)
    return trigger


@router.get("/", response_model=List[TriggerRead])
def list_triggers(
    user_telegram_id: int = Query(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.telegram_id == user_telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    triggers = (
        db.query(Trigger)
        .filter(Trigger.user_id == user.id)
        .order_by(Trigger.created_at.asc())
        .all()
    )
    return triggers

@router.get("/limit")
def get_trigger_limit_info(
    user_telegram_id: int = Query(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.telegram_id == user_telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "telegram_id": user.telegram_id,
        "plan": user.plan.value,
        "limit": user.trigger_limit,
        "current_count": user.trigger_count,
        "remaining": max(0, user.trigger_limit - user.trigger_count),
        "worker_active": bool(user.worker_active),
        "is_registered": bool(user.is_registered),
        "can_create": user.can_create_trigger,
    }

@router.post("/check")
def check_trigger(data: dict, db: Session = Depends(get_db)):
    user_telegram_id = data.get("telegram_id")
    msg = data.get("message", "").lower()

    user = db.query(User).filter_by(telegram_id=user_telegram_id).first()
    if not user:
        return {"reply_text": None}

    triggers = db.query(Trigger).filter_by(user_id=user.id).all()

    for t in triggers:
        if t.trigger_text in msg:  # contains match
            return {"reply_text": t.reply_text}

    return {"reply_text": None}


@router.delete("/{trigger_id}")
def delete_trigger(trigger_id: int, db: Session = Depends(get_db)):
    trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    db.delete(trigger)
    user = db.query(User).filter(User.id == trigger.user_id).first()
    if user and user.trigger_count > 0:
        user.trigger_count -= 1
    db.commit()
    return {"detail": "Deleted"}


@router.patch("/{trigger_id}", response_model=TriggerRead)
def update_trigger(
    trigger_id: int,
    payload: TriggerUpdate,
    db: Session = Depends(get_db),
):
    trigger = db.query(Trigger).filter(Trigger.id == trigger_id).first()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    if payload.trigger_text is not None:
        trigger.trigger_text = payload.trigger_text.lower()
    if payload.reply_text is not None:
        trigger.reply_text = payload.reply_text
    if payload.is_active is not None:
        trigger.is_active = payload.is_active

    db.commit()
    db.refresh(trigger)
    return trigger