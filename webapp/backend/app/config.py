from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Shared with the legacy Streamlit app: Accounting/data/BankTransactions
DEFAULT_BANK_TRANSACTIONS_DIR = Path(__file__).resolve().parents[3] / "data" / "BankTransactions"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Bearer token required on all API routes except /health.
    accounting_api_token: str = "dev-local-token"
    cors_origins: list[str] = ["http://localhost:3000"]
    bank_transactions_dir: Path = DEFAULT_BANK_TRANSACTIONS_DIR


@lru_cache
def get_settings() -> Settings:
    return Settings()
