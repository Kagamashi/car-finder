from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://car_finder:car_finder@db:5432/car_finder"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # SMTP
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "Car Finder <noreply@car-finder.local>"
    SMTP_USE_TLS: bool = True

    # Application
    LOG_LEVEL: str = "INFO"
    SCRAPE_INTERVAL_SECONDS: int = 300
    ADMIN_API_KEY: str = "change-me"


settings = Settings()
