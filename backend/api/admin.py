from datetime import datetime, timedelta
from typing import List
from sqlalchemy import text
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

import httpx
from backend.core.config import settings
from backend.core.db import get_db
from backend.models.user import User, PlanEnum
from backend.models.admin import Admin

router = APIRouter(prefix="/admin", tags=["admin"])


# ============================
#        PAYLOADS
# ============================
class AdminAddPayload(BaseModel):
    requester_telegram_id: int
    new_admin_telegram_id: int


class AdminRemovePayload(BaseModel):
    requester_telegram_id: int
    admin_telegram_id: int


class GiftPayload(BaseModel):
    requester_telegram_id: int
    target_telegram_id: int
    plan: PlanEnum


# ============================
#        HELPERS
# ============================

def require_admin(telegram_id: int, db: Session) -> Admin:
    admin = (
        db.query(Admin)
        .filter(Admin.telegram_id == telegram_id, Admin.is_active == True)
        .first()
    )
    if not admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return admin


# ============================
#        ADMINS
# ============================

@router.get("/admins", response_model=List[int])
def list_admins(
    requester_telegram_id: int,
    db: Session = Depends(get_db),
):
    require_admin(requester_telegram_id, db)
    admins = db.query(Admin).filter(Admin.is_active == True).all()
    return [a.telegram_id for a in admins]


@router.post("/admins/add")
def add_admin(
    payload: AdminAddPayload,
    db: Session = Depends(get_db),
):
    require_admin(payload.requester_telegram_id, db)
    new_admin_telegram_id = payload.new_admin_telegram_id

    exists = db.query(Admin).filter(Admin.telegram_id == new_admin_telegram_id).first()
    if exists:
        if exists.is_active:
            raise HTTPException(status_code=409, detail="Admin already exists")
        exists.is_active = True
        exists.created_at = datetime.utcnow()
        db.commit()
        return {"detail": "Admin re-activated"}

    admin = Admin(
        telegram_id=new_admin_telegram_id,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(admin)
    db.commit()
    return {"detail": "Admin added"}


@router.post("/admins/remove")
def remove_admin(
    payload: AdminRemovePayload,
    db: Session = Depends(get_db),
):
    require_admin(payload.requester_telegram_id, db)
    admin_telegram_id = payload.admin_telegram_id

    admin = db.query(Admin).filter(Admin.telegram_id == admin_telegram_id).first()
    if not admin or not admin.is_active:
        raise HTTPException(status_code=404, detail="Admin not found")

    admin.is_active = False
    db.commit()
    return {"detail": "Admin removed"}


# ============================
#        USERS
# ============================

@router.get("/users/stats")
def users_stats(
    requester_telegram_id: int,
    db: Session = Depends(get_db),
):
    require_admin(requester_telegram_id, db)

    total = db.query(User).count()
    free = db.query(User).filter(User.plan == PlanEnum.free).count()
    pro = db.query(User).filter(User.plan == PlanEnum.pro).count()
    premium = db.query(User).filter(User.plan == PlanEnum.premium).count()

    return {
        "total": total,
        "free": free,
        "pro": pro,
        "premium": premium,
    }


@router.get("/users/{telegram_id}")
def get_user_by_telegram_id(
    telegram_id: int,
    requester_telegram_id: int,
    db: Session = Depends(get_db),
):
    require_admin(requester_telegram_id, db)

    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "telegram_id": user.telegram_id,
        "name": user.name or "not provided",
        "username": f"@{user.username}" if user.username else "not provided",
        "phone": user.phone or "not provided",
        "plan": user.plan.value,
        "plan_expires_at": user.plan_expires_at,
        "registered_at": user.registered_at,
        "created_at": user.created_at,
        "worker_active": bool(user.worker_active),
        "last_seen_at": user.last_seen_at,
        "trigger_count": user.trigger_count,
        "is_registered": bool(user.is_registered),
    }


@router.post("/users/gift")
def gift_user_plan(
    payload: GiftPayload,
    db: Session = Depends(get_db),
):
    require_admin(payload.requester_telegram_id, db)

    user = db.query(User).filter(User.telegram_id == payload.target_telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    expires_at = datetime.utcnow() + timedelta(days=30)

    user.plan = payload.plan
    user.plan_expires_at = expires_at
    db.commit()

    # ============================
    # TELEGRAM NOTIFICATION
    # ============================
    try:
        plan_name = payload.plan.value.upper()

        text = (
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            f"Sizga <b>GhostReply</b> tomonidan\n"
            f"⭐ <b>{plan_name}</b> tarif (1 oy) sovg‘a qilindi.\n\n"
            f"⏳ <b>Amal qilish muddati:</b>\n"
            f"{expires_at.strftime('%Y-%m-%d')}\n\n"
            "Yangi imkoniyatlardan foydalaning 🚀"
        )

        async def send_message():
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": user.telegram_id,
                        "text": text,
                        "parse_mode": "HTML",
                    },
                    timeout=10,
                )

        import asyncio
        asyncio.create_task(send_message())

    except Exception as e:
        # XATO bo‘lsa ham gift bekor bo‘lmaydi
        print(f"⚠️ Failed to send gift notification: {e}")

    return {
        "detail": f"{payload.plan.value} gifted for 30 days",
        "telegram_id": payload.target_telegram_id,
        "plan": payload.plan.value,
        "expires_at": expires_at,
    }


@router.get("/check/{telegram_id}")
def check_admin(
    telegram_id: int,
    db: Session = Depends(get_db),
):
    admin = (
        db.query(Admin)
        .filter(
            Admin.telegram_id == telegram_id,
            Admin.is_active == True
        )
        .first()
    )

    if not admin:
        raise HTTPException(status_code=403, detail="Not an admin")

    return {"ok": True}


@router.get("/users")
def get_admin_users(
    requester_telegram_id: int,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    require_admin(requester_telegram_id, db)

    query = db.query(User).order_by(User.created_at.desc())

    total = query.count()

    users = (
        query
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for u in users:
        items.append({
            "telegram_id": u.telegram_id,
            "name": u.name or "not provided",
            "username": f"@{u.username}" if u.username else "not provided",
            "phone": u.phone or "not provided",
            "plan": u.plan.value,
            "plan_expires_at": u.plan_expires_at,
            "created_at": u.created_at,
            "worker_active": bool(u.worker_active),
            "last_seen_at": u.last_seen_at,
            "trigger_count": u.trigger_count,
            "is_registered": bool(u.is_registered),
        })

    return {
        "total": total,
        "items": items,
    }