from datetime import datetime, timedelta
import logging

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from backend.core.db import get_db
from backend.models.telegram_session import TelegramSession
from backend.models.user import PlanEnum, User
from backend.models.admin import Admin
from backend.schemas.user import UserCreate, UserRead, UserUpdatePhone

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

    # 🔑 SESSION STRINGNI ANIQLAYMIZ
    session_string = (
        user.telegram_session.session_string
        if user.telegram_session
        else None
    )

    # 🔒 HAQIQIY (EFFECTIVE) HOLAT
    effective_is_registered = bool(user.is_registered and session_string)
    effective_worker_active = bool(user.worker_active and session_string)

    is_admin = (
        db.query(Admin)
        .filter(
            Admin.telegram_id == user.telegram_id,
            Admin.is_active.is_(True),
        )
        .first()
        is not None
    )

    # ✅ BOT VA MIDDLEWARE SHU JSON’GA ISHONADI
    return {
        "telegram_id": user.telegram_id,
        "name": user.name,
        "username": user.username,
        "is_admin": is_admin,
        "phone": user.phone,
        "plan": user.plan,

        # 🔥 MUHIM QISM
        "is_registered": effective_is_registered,
        "worker_active": effective_worker_active,

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


@router.post("/claim")
def claim_users(
    limit: int = 50,
    worker_id: str = Depends(get_worker_id),
    db: Session = Depends(get_db),
):
    STALE_AFTER = timedelta(seconds=45)
    now = datetime.utcnow()

    try:
        rows = (
            db.query(User, TelegramSession.session_string)
            .join(TelegramSession, TelegramSession.user_id == User.id)
            .filter(
                User.is_registered.is_(True),
                TelegramSession.session_string.isnot(None),
                or_(
                    User.worker_id.is_(None),
                    and_(
                        User.last_seen_at.isnot(None),
                        User.last_seen_at < now - STALE_AFTER,
                    ),
                ),
                or_(
                    User.worker_active.is_(False),
                    User.worker_id.is_(None),
                ),
            )
            .order_by(User.last_seen_at.asc().nullslast())
            .limit(limit)
            .with_for_update(of=User, skip_locked=True)
            .all()
        )

        if not rows:
            return []

        for u, _session in rows:
            u.worker_id = worker_id
            u.worker_active = True

        db.commit()

        return [
            {
                "telegram_id": u.telegram_id,
                "session_string": session_string,
            }
            for (u, session_string) in rows
        ]

    except Exception:
        # 🔥 MANA SHU YERGA
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
    users = (
        db.query(User)
        .options(joinedload(User.telegram_session))
        .filter(
            User.worker_active.is_(True),
            User.telegram_session.has(TelegramSession.session_string.isnot(None)),
        )
        .all()
    )

    return [
        {
            "telegram_id": u.telegram_id,
            "session_string": u.telegram_session.session_string if u.telegram_session else None,
        }
        for u in users
    ]


@router.get("/with-sessions")
def get_users_with_sessions(db: Session = Depends(get_db)):
    users = (
        db.query(User)
        .options(joinedload(User.telegram_session))
        .filter(
            User.worker_id.is_(None),
            User.is_registered.is_(True),
            User.telegram_session.has(TelegramSession.session_string.isnot(None)),
        )
        .all()
    )

    return [
        {
            "telegram_id": u.telegram_id,
            "session_string": u.telegram_session.session_string if u.telegram_session else None,
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
    user.username = data.username

    # Save session into TelegramSession (1-to-1)
    tg_session = (
        db.query(TelegramSession)
        .filter(TelegramSession.user_id == user.id)
        .first()
    )
    if not tg_session:
        tg_session = TelegramSession(
            user_id=user.id,
            telegram_id=user.telegram_id,
            session_string=data.session_string,
        )
        db.add(tg_session)
    else:
        tg_session.session_string = data.session_string

    # Registration completed
    user.is_registered = True
    user.registered_at = datetime.utcnow()

    # Make user re-claimable by workers; heartbeat will set active
    user.worker_id = None
    user.worker_active = False
    user.last_seen_at = None

    db.commit()
    db.refresh(user)
    return {"status": "ok"}


# =========================
# Heartbeat
# =========================
@router.post("/heartbeat/{telegram_id}")
def heartbeat(telegram_id: int, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .options(joinedload(User.telegram_session))
        .filter(User.telegram_id == telegram_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 🔒 HARD GUARD: no session = no heartbeat
    if not user.telegram_session or not user.telegram_session.session_string:
        user.worker_active = False
        user.worker_id = None
        db.commit()
        raise HTTPException(status_code=403, detail="Session not active")

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
    user.worker_id = None
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

    # ✅ TELEGRAM SESSIONNI BUTUNLAY O‘CHIRAMIZ
    if user.telegram_session:
        db.delete(user.telegram_session)

    user.worker_active = False
    user.worker_id = None
    user.last_seen_at = None

    # ❗ MUHIM: is_registered NI O‘CHIRMAYMIZ
    # user.is_registered = False  ❌ YO‘Q

    db.commit()
    return {"status": "revoked"}


@router.get("/{telegram_id}/connection-status")
def connection_status(telegram_id: int, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .options(joinedload(User.telegram_session))
        .filter(User.telegram_id == telegram_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    has_session = bool(
        user.telegram_session and user.telegram_session.session_string
    )

    return {
        "telegram_id": telegram_id,
        "connected": has_session,
        "worker_active": user.worker_active if has_session else False,
    }