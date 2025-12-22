from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.core.db import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/users")
def get_analytics_users(db: Session = Depends(get_db)):
    query = text("SELECT * FROM analytics_users_v")
    result = db.execute(query)

    rows = result.mappings().all()
    return rows