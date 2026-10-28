from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Shared with the legacy Streamlit app: Accounting/data/BankTransactions
DEFAULT_BANK_TRANSACTIONS_DIR = Path(__file__).resolve().parents[3] / "data" / "BankTransactions"
# Root folder for scanned/photographed receipts, organized in quarter subfolders
# (e.g. data/Receipts/2026-Q1/...) — never committed, see root .gitignore.
DEFAULT_RECEIPTS_DIR = Path(__file__).resolve().parents[3] / "data" / "Receipts"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Bearer token required on all API routes except /health.
    accounting_api_token: str = "dev-local-token"
    cors_origins: list[str] = ["http://localhost:3000"]
    bank_transactions_dir: Path = DEFAULT_BANK_TRANSACTIONS_DIR
    receipts_dir: Path = DEFAULT_RECEIPTS_DIR


@lru_cache
def get_settings() -> Settings:
    return Settings()
