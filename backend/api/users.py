from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import logging
from datetime import datetime, timedelta
from sqlalchemy import or_, and_
from datetime import datetime, timedelta
from sqlalchemy import or_, and_
from backend.models.telegram_session import TelegramSession

from sqlalchemy.orm import joinedload

from backend.models.telegram_session import TelegramSession
from backend.core.db import get_db
from backend.models.user import User, PlanEnum
from backend.schemas.user import (
    UserCreate,
    UserRead,
    UserUpdatePhone,
)

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)


@router.get("/{telegram_id}")
def get_user(telegram_id: int, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .options(joinedload(User.telegram_session))
        .filter(User.telegram_id == telegram_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    session_string = None
    if user.telegram_session and user.telegram_session.session_string:
        session_string = user.telegram_session.session_string

    # JSON qilib qaytaramiz (bot shu JSON’ni ishlatadi)
    return {
        "telegram_id": user.telegram_id,
        "name": user.name,
        "username": user.username,
        "phone": user.phone,
        "plan": user.plan,
        "is_registered": user.is_registered,
        "worker_active": user.worker_active,
        "worker_id": user.worker_id,
        "last_seen_at": user.last_seen_at.isoformat() if user.last_seen_at else None,
        "session_string": session_string,
    }

# =========================
# Worker authentication
# =========================
def get_worker_id(
    x_worker_id: str = Header(..., alias="X-Worker-ID"),
):
    if not x_worker_id:
        raise HTTPException(status_code=400, detail="X-Worker-ID header missing")
    return x_worker_id


# =========================
# Worker → claim users
# =========================
@router.post("/claim")
def claim_users(
    limit: int = 50,
    worker_id: str = Depends(get_worker_id),
    db: Session = Depends(get_db),
):
    STALE_AFTER = timedelta(seconds=45)
    now = datetime.utcnow()

    try:
        users = (
            db.query(User)
            .options(joinedload(User.telegram_session))
            .filter(
                User.is_registered.is_(True),
                # faqat session mavjud bo‘lgan userlar
                User.telegram_session.has(TelegramSession.session_string.isnot(None)),
                or_(
                    User.worker_id.is_(None),
                    and_(
                        User.last_seen_at.isnot(None),
                        User.last_seen_at < now - STALE_AFTER,
                    ),
                ),
            )
            .order_by(User.last_seen_at.asc().nullslast())
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
                "session_string": u.telegram_session.session_string if u.telegram_session else None,
            }
            for u in users
        ]

    except Exception:
        db.rollback()
        logger.exception("CLAIM_USERS_FATAL")
        return []

# =========================
# User registration
# =========================
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


# =========================
# Active users
# =========================
@router.get("/active")
def get_active_users(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.worker_active.is_(True)).all()
    return [
        {
            "telegram_id": u.telegram_id,
            "session_string": u.session_string,
        }
        for u in users
    ]


@router.get("/with-sessions")
def get_users_with_sessions(db: Session = Depends(get_db)):
    users = (
        db.query(User)
        .filter(
            User.worker_id.is_(None),
            User.session_string.isnot(None),
            User.is_registered.is_(True),
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



# =========================
# Complete registration
# =========================
class CompleteRegistrationRequest(BaseModel):
    telegram_id: int
    phone: str
    session_string: str
    username: str | None = None


@router.post("/complete-registration")
def complete_registration(
    data: CompleteRegistrationRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.telegram_id == data.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.phone = data.phone
    user.session_string = data.session_string
    user.username = data.username
    # This is the ONLY place where registration is completed
    user.is_registered = True
    user.worker_active = True
    user.registered_at = datetime.utcnow()

    db.commit()
    db.refresh(user)
    return {"status": "ok"}


# =========================
# Heartbeat
# =========================
@router.post("/heartbeat/{telegram_id}")
def heartbeat(telegram_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.worker_active = True
    user.last_seen_at = datetime.utcnow()

    db.commit()
    return {"status": "ok"}


# =========================
# Update phone
# =========================
@router.post("/update_phone", response_model=UserRead)
def update_phone(
    data: UserUpdatePhone,
    telegram_id: int,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.phone = data.phone
    # Phone update does NOT mean full registration
    # user.is_registered and user.registered_at are NOT set here

    db.commit()
    db.refresh(user)
    return user


# =========================
# Worker disconnected
# =========================
@router.post("/worker-disconnected/{telegram_id}")
def worker_disconnected(telegram_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.worker_active = False
    user.last_seen_at = None
    db.commit()

    return {"status": "disconnected"}

@router.post("/session-revoked/{telegram_id}")
def session_revoked(telegram_id: int, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .options(joinedload(User.telegram_session))
        .filter(User.telegram_id == telegram_id)
        .first()
    )
    if not user:
        return {"status": "ignored"}

    # TelegramSession’ni tozalaymiz
    if user.telegram_session:
        user.telegram_session.session_string = None

    user.is_registered = False
    user.worker_active = False
    user.worker_id = None
    user.last_seen_at = None

    db.commit()
    return {"status": "revoked"}