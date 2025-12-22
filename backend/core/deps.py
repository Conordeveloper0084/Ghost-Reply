# backend/core/deps.py
from fastapi import Header, HTTPException

def get_worker_id(x_worker_id: str = Header(None)):
    if not x_worker_id:
        raise HTTPException(status_code=400, detail="X-Worker-ID header missing")
    return x_worker_id