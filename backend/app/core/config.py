from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = "MilestoneMate AI"
    app_env: str = "development"

    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # AI configuration
    ai_mode: str = "live"
    llm_provider: str = "gemini"
    ai_timeout_seconds: int = 45
    ai_max_retries: int = 2
    ai_calls_per_user_per_hour: int = 20

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"

    # Payment configuration
    payments_mode: str = "mock"

    paypal_api_base: str = "https://api-m.sandbox.paypal.com"
    paypal_client_id: str | None = None
    paypal_client_secret: str | None = None
    paypal_webhook_id: str | None = None

    payee_mode: str = "demo_merchant"
    paypal_brand_name: str = "MilestoneMate AI"

    frontend_base_url: str = "http://localhost:5173"

    allow_unverified_webhooks_in_mock: bool = False

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()