from fastapi import Header, HTTPException, status

from .config import get_settings


def require_api_key(x_api_key: str = Header(default="")) -> None:
    settings = get_settings()
    if not x_api_key or x_api_key != settings.accounting_api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
