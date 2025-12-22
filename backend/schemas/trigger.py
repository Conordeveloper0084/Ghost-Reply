from datetime import datetime
from typing import Optional

from pydantic import BaseModel

class TriggerBase(BaseModel):
    trigger_text: str
    reply_text: str


class TriggerCreate(TriggerBase):
    user_telegram_id: int  # botdan keladigan user identifikatori


class TriggerRead(BaseModel):
    id: int
    trigger_text: str
    reply_text: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TriggerUpdate(BaseModel):
    trigger_text: Optional[str] = None
    reply_text: Optional[str] = None
    is_active: Optional[bool] = None