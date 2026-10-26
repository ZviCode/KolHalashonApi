from __future__ import annotations

import base64
import binascii
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Treat a token as expired a little before it really is.
_EXPIRY_MARGIN = timedelta(minutes=5)


def decode_jwt_payload(token: str) -> dict[str, Any] | None:
    """Return the (unverified) payload of a JWT, or ``None`` if it is not one."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        data = json.loads(base64.urlsafe_b64decode(payload))
    except (binascii.Error, ValueError):
        return None
    return data if isinstance(data, dict) else None


class SessionManager:
    """Holds the HTTP session and the login token, optionally persisted as JSON."""

    def __init__(
        self,
        session_file: str | os.PathLike[str] | None = "kolhalashon_session.json",
        session: requests.Session | None = None,
    ) -> None:
        self.session_file = Path(session_file) if session_file else None
        self.session = session or requests.Session()
        self.auth_token: str | None = None
        self.user_id: int | None = None

    @property
    def token_expiry(self) -> datetime | None:
        if not self.auth_token:
            return None
        payload = decode_jwt_payload(self.auth_token)
        exp = payload.get("exp") if payload else None
        return (
            datetime.fromtimestamp(exp, tz=timezone.utc) if isinstance(exp, (int, float)) else None
        )

    def is_token_valid(self) -> bool:
        """Check the token locally. Tokens without a readable expiry are assumed valid."""
        if not self.auth_token:
            return False
        expiry = self.token_expiry
        if expiry is None:
            return True
        return datetime.now(timezone.utc) + _EXPIRY_MARGIN < expiry

    def load_session(self) -> bool:
        """Load a saved token. Returns ``False`` when there is nothing usable to load."""
        if not self.session_file or not self.session_file.exists():
            return False
        try:
            data = json.loads(self.session_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning("Ignoring unreadable session file %s: %s", self.session_file, exc)
            return False
        if not isinstance(data, dict):
            return False
        self.auth_token = data.get("auth_token")
        self.user_id = data.get("user_id")
        cookies = data.get("cookies")
        if isinstance(cookies, dict):
            self.session.cookies.update(cookies)
        logger.debug("Session loaded from %s", self.session_file)
        return self.auth_token is not None

    def save_session(self) -> None:
        if not self.session_file:
            return
        data = {
            "auth_token": self.auth_token,
            "user_id": self.user_id,
            "cookies": self.session.cookies.get_dict(),
        }
        # The file holds a login token: create it readable by the owner only.
        fd = os.open(self.session_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file)
        logger.debug("Session saved to %s", self.session_file)

    def set_token(self, token: str, user_id: int | None = None) -> None:
        self.auth_token = token
        self.user_id = user_id
        self.save_session()

    def clear(self) -> None:
        self.auth_token = None
        self.user_id = None
        if self.session_file and self.session_file.exists():
            self.session_file.unlink()
