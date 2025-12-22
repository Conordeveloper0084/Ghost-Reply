from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from backend.models.user import PlanEnum


class UserBase(BaseModel):
    telegram_id: int
    name: Optional[str] = None
    phone: Optional[str] = None
    language: Optional[str] = "uz"


class UserCreate(UserBase):
    """Yangi user registratsiya uchun schema"""
    pass


class UserRead(BaseModel):
    id: int
    telegram_id: int
    name: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    language: Optional[str] = "uz"
    plan: PlanEnum
    is_registered: bool
    worker_active: bool
    worker_id: Optional[str] = None 
    registered_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdatePlan(BaseModel):
    plan: PlanEnum


class UserSummary(BaseModel):
    telegram_id: int
    name: str
    plan: PlanEnum
    triggers_used: int
    trigger_limit: int

    class Config:
        from_attributes = True 


class UserUpgradeRequest(BaseModel):
    telegram_id: int
    new_plan: str


class UserUpdatePhone(BaseModel):
    phone: str