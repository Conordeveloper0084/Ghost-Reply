from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles

from backend.api import users, triggers, payment, admin, analytics
from Frontend.web_login import router as web_login_router
from backend.core import cron


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Starts background cron/heartbeat watcher exactly once when API boots.
    IMPORTANT:
    - Keep this function LIGHT.
    - Do NOT run DB migrations or heavy queries here.
    """
    starter = getattr(cron, "start", None) or getattr(cron, "start_cron", None)
    if starter:
        starter()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    """
    Healthcheck endpoint for Docker / orchestration.
    Must return 200 immediately when app is up.
    """
    return {"status": "ok"}


# API routers
app.include_router(users.router, prefix="/api")
app.include_router(triggers.router, prefix="/api")
app.include_router(payment.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")

# Web-login router (HTML)
app.include_router(web_login_router)  # /web-login/...

# Static assets
app.mount(
    "/images",
    StaticFiles(directory="Frontend/public/images"),
    name="images",
)