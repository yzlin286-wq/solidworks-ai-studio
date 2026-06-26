from __future__ import annotations

import os
from fastapi import Header, HTTPException, status


def configured_token() -> str:
    return os.environ.get("SWAI_API_TOKEN", "dev-token")


def require_api_token(x_swai_token: str | None = Header(default=None)) -> None:
    expected = configured_token()
    if not expected:
        return
    if x_swai_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing SolidWorks AI Studio API token.",
        )
