from pydantic import BaseModel
from typing import Optional


class AnalystUserRead(BaseModel):
    telegram_id: int
    plan: str
    plan_expires_at: Optional[str]
    registered_at: Optional[str]
    worker_active: bool
    trigger_count: int