import asyncio
from datetime import datetime, timedelta
from sqlalchemy import text

from backend.core.db import SessionLocal
from backend.models.user import User, PlanEnum

CHECK_EVERY = 60
TIMEOUT = 90
PLAN_CHECK_EVERY = 300
ANALYTICS_REFRESH_EVERY = 300


# 🔒 BU YERDA GLOBAL FLAG
_started = False


async def worker_watchdog():
    while True:
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(seconds=TIMEOUT)

            users = db.query(User).filter(
                User.worker_active == True,
                User.last_seen_at.isnot(None),
                User.last_seen_at < cutoff
            ).all()

            if users:
                for u in users:
                    u.worker_active = False
                    u.worker_id = None
                    u.last_seen_at = None

                db.commit()
                print(f"🧹 watchdog released {len(users)} stale users")

        except Exception as e:
            db.rollback()
            print("❌ watchdog error:", e)

        finally:
            db.close()

        await asyncio.sleep(CHECK_EVERY)

async def plan_expiry_watcher():
    while True:
        db = SessionLocal()
        try:
            now = datetime.utcnow()

            expired_users = db.query(User).filter(
                User.plan != PlanEnum.free,
                User.plan_expires_at.isnot(None),
                User.plan_expires_at <= now
            ).all()

            if expired_users:
                for user in expired_users:
                    user.plan = PlanEnum.free
                    user.plan_expires_at = None
                db.commit()
        finally:
            db.close()

        await asyncio.sleep(PLAN_CHECK_EVERY)


async def analytics_refresher():
    while True:
        db = SessionLocal()
        try:
            db.execute(
                text("REFRESH MATERIALIZED VIEW CONCURRENTLY analytics_users_mv")
            )
            db.commit()
            print("✅ analytics_users_mv refreshed")
        except Exception as e:
            db.rollback()
            print("❌ analytics refresh failed:", e)
        finally:
            db.close()

        await asyncio.sleep(ANALYTICS_REFRESH_EVERY)


# 🚀 FAQAT SHU FUNKSIYAGA QO‘SHAMIZ
def start():
    global _started

    if _started:
        print("⚠️ cron already started, skipping")
        return

    _started = True
    print("🚀 cron started")

    loop = asyncio.get_running_loop()
    loop.create_task(worker_watchdog())
    loop.create_task(plan_expiry_watcher())
    loop.create_task(analytics_refresher())