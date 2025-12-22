from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    BOT_TOKEN: str

    # Backend service URL (used by workers / internal calls)
    BACKEND_URL: str = "http://backend:8000/api"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )


settings = Settings()