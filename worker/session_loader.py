# worker/session_loader.py
import httpx
from worker.config import BACKEND_URL
from worker.config import WORKER_ID, MAX_CLIENTS

async def claim_users_for_worker():
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.post(
            f"{BACKEND_URL}/api/users/claim",
            params={"limit": MAX_CLIENTS},
            headers={"X-Worker-ID": WORKER_ID},
        )
        res.raise_for_status()
        return res.json()