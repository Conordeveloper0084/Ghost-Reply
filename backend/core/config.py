from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # === DATABASE ===
    DATABASE_URL: str

    # === TELEGRAM (backend majburiy emas, lekin env’da bo‘lishi mumkin) ===
    TELEGRAM_API_ID: Optional[int] = None
    TELEGRAM_API_HASH: Optional[str] = None
    BOT_TOKEN: Optional[str] = None

    # === BACKEND URL (worker / bot uchun, backend o‘zi ishlatmaydi) ===
    BACKEND_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )


settings = Settings()