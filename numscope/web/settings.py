"""Web-specific settings, all from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, default)))
    except (TypeError, ValueError):
        return default


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class WebSettings:
    #: Requests allowed per client IP per window.
    rate_limit: int = 10
    rate_window: int = 60
    #: Requests allowed across ALL clients per window (anti-botnet).
    global_limit: int = 120
    #: Call optional providers (e.g. Numverify) from the public site?
    enable_providers: bool = False
    #: Max provider calls per UTC day, to protect a free-tier quota.
    daily_provider_cap: int = 50
    #: Number of reverse-proxy hops in front of the app (0 = none).
    trusted_proxy_hops: int = 0

    @classmethod
    def from_env(cls) -> "WebSettings":
        return cls(
            rate_limit=_int("WEB_RATE_LIMIT", 10),
            rate_window=max(1, _int("WEB_RATE_WINDOW", 60)),
            global_limit=_int("WEB_GLOBAL_LIMIT", 120),
            enable_providers=_bool("WEB_ENABLE_PROVIDERS", False),
            daily_provider_cap=_int("WEB_DAILY_PROVIDER_CAP", 50),
            trusted_proxy_hops=_int("TRUST_PROXY_HOPS", 0),
        )
