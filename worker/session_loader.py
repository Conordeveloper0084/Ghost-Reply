# worker/session_loader.py
import httpx
import logging

from worker.config import BACKEND_URL
from worker.config import WORKER_ID, MAX_CLIENTS

logger = logging.getLogger(__name__)

async def claim_users_for_worker():
    logger.info(f"🔗 Worker attempting to reach backend at: {BACKEND_URL}")

    async with httpx.AsyncClient(timeout=10) as client:
        # ---- Preflight health check (DNS + connectivity validation)
        try:
            health = await client.get(f"{BACKEND_URL}/health")
            logger.info(f"💚 Backend health check OK ({health.status_code})")
        except Exception as e:
            logger.error(f"❌ Backend health check failed: {repr(e)}")
            return []

        # ---- Claim users
        try:
            res = await client.post(
                f"{BACKEND_URL}/api/users/claim",
                params={"limit": MAX_CLIENTS},
                headers={"X-Worker-ID": WORKER_ID},
            )
            res.raise_for_status()
            return res.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"❌ Backend responded with error "
                f"{e.response.status_code}: {e.response.text}"
            )
            return []

        except Exception as e:
            logger.error(f"❌ Claim users failed: {repr(e)}")
            return []