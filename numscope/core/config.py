"""Configuration loading. Missing keys never raise."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_TRUTHY = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in _TRUTHY


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_str(name: str) -> Optional[str]:
    value = (os.getenv(name) or "").strip()
    return value or None


@dataclass(frozen=True)
class Config:
    numverify_api_key: Optional[str] = None
    numverify_allow_http: bool = False
    http_timeout: float = 10.0
    user_agent: str = "numscope/1.0 (+OSINT research tool)"

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "Config":
        """Load .env (if python-dotenv is present) then read variables."""
        try:
            from dotenv import load_dotenv
        except ImportError:  # dotenv is optional at runtime
            load_dotenv = None

        if load_dotenv is not None:
            if env_file:
                candidates = [Path(env_file)]
            else:
                repo_root = Path(__file__).resolve().parents[1]
                candidates = [Path.cwd() / ".env", repo_root / ".env"]
            for path in candidates:
                if path.is_file():
                    load_dotenv(path, override=False)
                    break

        return cls(
            numverify_api_key=_env_str("NUMVERIFY_API_KEY"),
            numverify_allow_http=_env_bool("NUMVERIFY_ALLOW_HTTP"),
            http_timeout=_env_float("HTTP_TIMEOUT", 10.0),
        )
