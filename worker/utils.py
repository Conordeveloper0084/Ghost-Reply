from typing import Generic, TypeVar, Optional, Dict, Tuple
import time
import re

import signal
from sqlalchemy import text
from backend.core.db import engine
from worker.config import WORKER_ID

T = TypeVar('T')

def normalize_text(text: str) -> str:
    """
    Normalize text for safer Telegram messages by removing control characters,
    trimming whitespace, and converting to lowercase.
    """
    # Remove control characters (except newline and tab)
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
    return text.lower().strip()

class TTLCache(Generic[T]):
    """
    Simple in-memory TTL cache with type hints and cleanup.
    """
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl: int = ttl_seconds
        self.store: Dict[str, Tuple[T, float]] = {}

    def get(self, key: str) -> Optional[T]:
        item = self.store.get(key)
        if item is None:
            return None

        value, ts = item
        if time.time() - ts > self.ttl:
            self.store.pop(key, None)
            return None

        return value

    def set(self, key: str, value: T) -> None:
        self.store[key] = (value, time.time())


def release_users():
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE users
            SET worker_id = NULL,
                worker_active = false
            WHERE worker_id = :worker_id
        """), {"worker_id": WORKER_ID})


def setup_shutdown_hooks():
    signal.signal(signal.SIGTERM, lambda *_: release_users())
    signal.signal(signal.SIGINT, lambda *_: release_users())
    signal.signal(signal.SIGQUIT, lambda *_: release_users())