# worker/main.py
import asyncio
import logging
import signal

import httpx
from telethon.errors import AuthKeyUnregisteredError, SessionRevokedError, UnauthorizedError

from worker.session_loader import claim_users_for_worker
from worker.client_manager import get_or_create_client
from worker.utils import setup_shutdown_hooks
from worker.config import (
    WORKER_ID,
    WORKER_POLL_INTERVAL,
    MAX_ACTIVE_TASKS,
    BACKEND_URL,
)

# Timing config (seconds)
HEARTBEAT_INTERVAL = 15
SESSION_CHECK_INTERVAL = 25
IDLE_SLEEP = 8
ERROR_SLEEP = 10

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

setup_shutdown_hooks()

ACTIVE_TASKS: dict[int, asyncio.Task] = {}
SHUTDOWN_EVENT = asyncio.Event()


async def reset_stale_workers_on_startup():
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.post(f"{BACKEND_URL}/api/users/reset-stale-workers")
            logger.info("♻️ Stale workers reset on startup")
        except Exception as e:
            logger.warning(f"⚠️ Failed to reset stale workers on startup: {e}")


async def heartbeat_loop(telegram_id: int):
    async with httpx.AsyncClient(timeout=5) as client:
        while not SHUTDOWN_EVENT.is_set():
            try:
                await client.post(
                    f"{BACKEND_URL}/api/users/heartbeat/{telegram_id}"
                )
            except Exception as e:
                logger.warning(f"💔 Heartbeat failed for {telegram_id}: {e}")
            await asyncio.sleep(HEARTBEAT_INTERVAL)



async def session_monitor(client, telegram_id: int):
    async with httpx.AsyncClient(timeout=5) as http:
        while not SHUTDOWN_EVENT.is_set():
            if not client.is_connected():
                break

            try:
                # REAL API ping (revoked bo‘lsa shu yerda yiqiladi)
                await client.get_me()
            except (AuthKeyUnregisteredError, SessionRevokedError, UnauthorizedError):
                logger.warning(f"🔌 Session revoked (monitor API) for {telegram_id}")

                # ikkalasini ham uramiz: session + worker status
                try:
                    await http.post(f"{BACKEND_URL}/api/users/session-revoked/{telegram_id}")
                    await http.post(f"{BACKEND_URL}/api/users/worker-disconnected/{telegram_id}")
                except Exception:
                    pass

                try:
                    await client.disconnect()
                except Exception:
                    pass
                break
            except Exception as e:
                logger.warning(f"⚠️ Session monitor error for {telegram_id}: {e}")

            await asyncio.sleep(SESSION_CHECK_INTERVAL)


async def start_client(user: dict):
    telegram_id = user["telegram_id"]
    session_string = user["session_string"]

    logger.info(f"🚀 Starting client for {telegram_id}")

    monitor_task = None
    heartbeat_task = None

    try:
        client = await get_or_create_client(telegram_id, session_string)

        if not await client.is_user_authorized():
            logger.warning(f"🔌 Session invalid at startup for {telegram_id}")
            async with httpx.AsyncClient(timeout=5) as http:
                await http.post(
                    f"{BACKEND_URL}/api/users/session-revoked/{telegram_id}"
                )
            return

        logger.info(f"🟢 Telegram session alive for {telegram_id}")

        # 🔥 Start heartbeat ONLY after successful auth
        heartbeat_task = asyncio.create_task(heartbeat_loop(telegram_id))

        monitor_task = asyncio.create_task(
            session_monitor(client, telegram_id)
        )

        await client.run_until_disconnected()

    except (AuthKeyUnregisteredError, SessionRevokedError, UnauthorizedError):
        logger.warning(f"🔌 Session revoked for {telegram_id}")
        async with httpx.AsyncClient(timeout=5) as http:
            await http.post(f"{BACKEND_URL}/api/users/session-revoked/{telegram_id}")
            await http.post(f"{BACKEND_URL}/api/users/worker-disconnected/{telegram_id}")

    except Exception as e:
        logger.exception(f"❌ Telegram client crashed for {telegram_id}: {e}")

    finally:
        if heartbeat_task:
            heartbeat_task.cancel()
        if monitor_task:
            monitor_task.cancel()

        await asyncio.gather(
            *( [heartbeat_task] if heartbeat_task else [] ),
            *( [monitor_task] if monitor_task else [] ),
            return_exceptions=True,
        )

        ACTIVE_TASKS.pop(telegram_id, None)
        logger.info(f"🧹 Cleaned up client for {telegram_id}")


async def graceful_shutdown():
    logger.warning("🛑 Shutting down worker gracefully")
    SHUTDOWN_EVENT.set()

    tasks = list(ACTIVE_TASKS.values())
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    ACTIVE_TASKS.clear()
    logger.info("✅ Worker shutdown complete")


async def worker_loop():
    logger.info(f"🧠 Worker {WORKER_ID} started")
    await reset_stale_workers_on_startup()

    while not SHUTDOWN_EVENT.is_set():
        try:
            if len(ACTIVE_TASKS) >= MAX_ACTIVE_TASKS:
                await asyncio.sleep(IDLE_SLEEP)
                continue

            users = await claim_users_for_worker()

            if not users:
                await asyncio.sleep(IDLE_SLEEP)
                continue

            for user in users:
                if len(ACTIVE_TASKS) >= MAX_ACTIVE_TASKS:
                    break

                telegram_id = user["telegram_id"]
                if telegram_id in ACTIVE_TASKS:
                    continue

                task = asyncio.create_task(start_client(user))
                ACTIVE_TASKS[telegram_id] = task
                logger.info(f"✅ User {telegram_id} claimed")

            await asyncio.sleep(WORKER_POLL_INTERVAL)

        except Exception as e:
            logger.error(f"❌ Worker loop error: {e}")
            await asyncio.sleep(ERROR_SLEEP)


def _handle_signal():
    asyncio.create_task(graceful_shutdown())


loop = asyncio.get_event_loop()
loop.add_signal_handler(signal.SIGTERM, _handle_signal)
loop.add_signal_handler(signal.SIGINT, _handle_signal)

if __name__ == "__main__":
    asyncio.run(worker_loop())