"""Numverify (apilayer) free-tier provider.

Free plans historically serve HTTP only. We default to HTTPS and refuse to
downgrade unless the user explicitly sets NUMVERIFY_ALLOW_HTTP=true,
because the API key travels in the query string.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from core.models import PhoneMetadata, ProviderResult
from modules.providers.base import BaseProvider

log = logging.getLogger(__name__)

ENDPOINT = "apilayer.net/api/validate"
HTTPS_RESTRICTED_CODE = 105


class NumverifyProvider(BaseProvider):
    name = "numverify"

    def is_configured(self) -> bool:
        return bool(self.config.numverify_api_key)

    def _scrub(self, text: str) -> str:
        key = self.config.numverify_api_key or ""
        return text.replace(key, "***") if key else text

    def lookup(self, meta: PhoneMetadata) -> ProviderResult:
        if not self.is_configured():
            return ProviderResult(self.name, False, error="No API key set.")
        if not (meta.parsed and meta.e164):
            return ProviderResult(self.name, False,
                                  error="Number could not be parsed.")
        try:
            import requests
        except ImportError:
            return ProviderResult(self.name, False,
                                  error="'requests' is not installed.")

        scheme = "http" if self.config.numverify_allow_http else "https"
        params = {
            "access_key": self.config.numverify_api_key,
            "number": meta.e164.lstrip("+"),
        }
        try:
            resp = requests.get(
                f"{scheme}://{ENDPOINT}",
                params=params,
                timeout=self.config.http_timeout,
                headers={"User-Agent": self.config.user_agent},
            )
            payload: Dict[str, Any] = resp.json()
        except requests.RequestException as exc:
            return ProviderResult(self.name, False,
                                  error=self._scrub(str(exc)))
        except ValueError:
            return ProviderResult(self.name, False,
                                  error="Non-JSON response from API.")

        if payload.get("success") is False:
            err = payload.get("error", {})
            msg = f"{err.get('code')}: {err.get('info') or err.get('type')}"
            result = ProviderResult(self.name, False, error=self._scrub(msg))
            if err.get("code") == HTTPS_RESTRICTED_CODE:
                result.notes.append(
                    "Free plan lacks HTTPS. Set NUMVERIFY_ALLOW_HTTP=true "
                    "only if you accept the key being sent unencrypted."
                )
            return result

        data = {
            k: payload.get(k)
            for k in ("valid", "line_type", "carrier", "location",
                      "country_name", "international_format", "local_format")
        }
        notes = []
        if scheme == "http":
            notes.append("Request was sent over plain HTTP.")
        return ProviderResult(self.name, True, data=data, notes=notes)
