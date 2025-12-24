import os
import uuid

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")

WORKER_POLL_INTERVAL = int(os.getenv("WORKER_POLL_INTERVAL", 5))
WORKER_LOG_LEVEL = os.getenv("WORKER_LOG_LEVEL", "INFO")
TRIGGER_CACHE_TTL = int(os.getenv("TRIGGER_CACHE_TTL", 10))

WORKER_ID = os.getenv("WORKER_ID", str(uuid.uuid4()))
MAX_CLIENTS = int(os.getenv("MAX_CLIENTS", 50))

# Maximum concurrent active tasks per worker
MAX_ACTIVE_TASKS = int(os.getenv("MAX_ACTIVE_TASKS", 20))

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://backend-server.railway.internal:8080"
)