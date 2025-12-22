import os
from dotenv import load_dotenv
import uuid

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

# ✅ MUHIM: Docker service name bilan
BACKEND_URL = "http://backend:8000"

WORKER_POLL_INTERVAL = int(os.getenv("WORKER_POLL_INTERVAL", 5))
WORKER_LOG_LEVEL = os.getenv("WORKER_LOG_LEVEL", "INFO")
TRIGGER_CACHE_TTL = int(os.getenv("TRIGGER_CACHE_TTL", 10))

WORKER_ID = os.getenv("WORKER_ID", str(uuid.uuid4()))
MAX_CLIENTS = int(os.getenv("MAX_CLIENTS", 50))

MAX_ACTIVE_TASKS = 20