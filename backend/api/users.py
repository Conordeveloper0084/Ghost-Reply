from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import bindparam
from sqlalchemy import select, update

from backend.core.db import get_db
from backend.models.user import User, PlanEnum
from backend.schemas.user import (
    UserCreate,
    UserRead,
    UserUpdatePhone,
)

router = APIRouter(prefix="/users", tags=["users"])

from backend.models.user import User
from backend.models.telegram_session import TelegramSession


# Worker authentication via header
def get_worker_id(
    x_worker_id: str = Header(..., alias="X-Worker-ID")
):
    return x_worker_id


@router.get("/with-sessions")
def get_users_with_sessions(db: Session = Depends(get_db)):
    users = (
        db.query(User)
        .filter(
            User.worker_active == True,
            User.session_string.isnot(None)
        )
        .all()
    )

    return [
        {
            "telegram_id": u.telegram_id,
            "session_string": u.session_string,
        }
        for u in users
    ]


@router.post("/claim")
def claim_users(
    limit: int = 50,
    worker_id: str = Depends(get_worker_id),
    db: Session = Depends(get_db),
):
    try:
        users = (
            db.query(User)
            .filter(User.worker_id.is_(None))
            .order_by(User.last_seen_at.desc().nullslast())
            .limit(limit)
            .with_for_update(skip_locked=True)
            .all()
        )

        if not users:
            return []

        for u in users:
            u.worker_id = worker_id
            u.worker_active = True

        db.commit()

        return [
            {
                "telegram_id": u.telegram_id,
                "session_string": u.session_string,
            }
            for u in users
        ]

    except Exception as e:
        db.rollback()
        print("CLAIM_USERS_FATAL:", repr(e))
        raise HTTPException(status_code=500, detail="claim_users failed")

@router.post("/register", response_model=UserRead)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == payload.telegram_id).first()
    if user:
        return user

    user = User(
        telegram_id=payload.telegram_id,
        name=payload.name,
        plan=PlanEnum.free,
        is_registered=False,
        worker_active=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


PLAN_LIMITS = {
    PlanEnum.free: 3,
    PlanEnum.pro: 10,
    PlanEnum.premium: 20,
}


@router.get("/active")
def get_active_users(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.worker_active == True).all()
    return [
        {
            "telegram_id": u.telegram_id,
            "session_string": u.session_string
        }
        for u in users
    ]


@router.get("/{telegram_id}", response_model=UserRead)
def get_user(telegram_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


class CompleteRegistrationRequest(BaseModel):
    telegram_id: int
    phone: str
    session_string: str
    username: str | None = None


@router.post("/complete-registration")
def complete_registration(data: CompleteRegistrationRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == data.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.phone = data.phone
    user.session_string = data.session_string
    user.username = data.username
    user.is_registered = True
    user.worker_active = True
    user.registered_at = datetime.utcnow()

    db.commit()
    db.refresh(user)
    return {"status": "ok"}


@router.post("/heartbeat/{telegram_id}")
def heartbeat(telegram_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.worker_active = True
    user.last_seen_at = datetime.utcnow()

    db.commit()
    return {"status": "ok"}




@router.post("/update_phone", response_model=UserRead)
def update_phone(
    data: UserUpdatePhone,
    telegram_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.phone = data.phone
    user.is_registered = True
    user.registered_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    return user

@router.post("/worker-disconnected/{telegram_id}")
def worker_disconnected(telegram_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.worker_active = False
    user.last_seen_at = None
    db.commit()

    return {"status": "disconnected"}