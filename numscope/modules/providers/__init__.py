"""Provider registry.

To add a service: subclass BaseProvider, then add the class to _CLASSES.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple, Type

from core.config import Config
from modules.providers.base import BaseProvider
from modules.providers.numverify import NumverifyProvider

_CLASSES: Sequence[Type[BaseProvider]] = (NumverifyProvider,)
PROVIDERS: Dict[str, Type[BaseProvider]] = {c.name: c for c in _CLASSES}


def load_providers(
    config: Config, requested: Optional[Sequence[str]] = None
) -> Tuple[List[BaseProvider], List[str]]:
    """Return (active providers, names skipped for missing credentials).

    Unconfigured providers are skipped silently, never an error.
    """
    names = list(requested) if requested else list(PROVIDERS)
    unknown = [n for n in names if n not in PROVIDERS]
    if unknown:
        raise ValueError(f"Unknown provider(s): {', '.join(unknown)}")

    active: List[BaseProvider] = []
    skipped: List[str] = []
    for name in names:
        provider = PROVIDERS[name](config)
        if provider.is_configured():
            active.append(provider)
        else:
            skipped.append(name)
    return active, skipped
