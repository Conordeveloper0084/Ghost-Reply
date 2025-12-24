# worker/main.py
import asyncio
import logging
import signal

import httpx

from worker.config import BACKEND_URL
from worker.session_loader import claim_users_for_worker
from worker.client_manager import get_or_create_client
from worker.utils import setup_shutdown_hooks
from worker.config import WORKER_ID, WORKER_POLL_INTERVAL, MAX_ACTIVE_TASKS

# Adaptive sleep timings (seconds)
ACTIVE_SLEEP = 0.5    # when users are claimed
IDLE_SLEEP = 8        # when no users are available
ERROR_SLEEP = 10      # on errors

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

setup_shutdown_hooks()

# telegram_id -> asyncio.Task
ACTIVE_TASKS: dict[int, asyncio.Task] = {}

SHUTDOWN_EVENT = asyncio.Event()

HEARTBEAT_INTERVAL = 15  # seconds


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


async def start_client(user: dict):
    telegram_id = user["telegram_id"]
    session_string = user["session_string"]

    logger.info(f"🚀 Starting client for {telegram_id}")

    heartbeat_task = asyncio.create_task(heartbeat_loop(telegram_id))

    try:
        client = await get_or_create_client(telegram_id, session_string)
        await client.run_until_disconnected()
    finally:
        heartbeat_task.cancel()
        await asyncio.gather(heartbeat_task, return_exceptions=True)

        logger.warning(f"⚠️ Client disconnected for {telegram_id}")
        ACTIVE_TASKS.pop(telegram_id, None)


async def graceful_shutdown():
    if SHUTDOWN_EVENT.is_set():
        return

    logger.warning("🛑 Shutdown signal received — stopping worker")

    SHUTDOWN_EVENT.set()

    tasks = list(ACTIVE_TASKS.values())
    if not tasks:
        logger.info("✅ No active clients, shutdown clean")
        return

    logger.info(f"🔻 Stopping {len(tasks)} active clients")

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    ACTIVE_TASKS.clear()

    logger.info("✅ All clients stopped, worker exited cleanly")


async def worker_loop():
    logger.info(f"🧠 Worker {WORKER_ID} started auto-claim loop")

    while not SHUTDOWN_EVENT.is_set():
        try:
            if len(ACTIVE_TASKS) >= MAX_ACTIVE_TASKS:
                logger.info(
                    f"⏸ Worker at capacity ({len(ACTIVE_TASKS)}/{MAX_ACTIVE_TASKS}), sleeping"
                )
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

                logger.info(f"✅ User {telegram_id} claimed & started")

            await asyncio.sleep(ACTIVE_SLEEP)

        except Exception as e:
            logger.error(f"❌ Worker loop error: {e}")
            await asyncio.sleep(ERROR_SLEEP)


async def main():
    loop = asyncio.get_running_loop()

    loop.add_signal_handler(
        signal.SIGTERM,
        lambda: asyncio.create_task(graceful_shutdown())
    )
    loop.add_signal_handler(
        signal.SIGINT,
        lambda: asyncio.create_task(graceful_shutdown())
    )

    await worker_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass