"""Provider interface. Subclass this to add a new lookup service."""
from __future__ import annotations

from abc import ABC, abstractmethod

from core.config import Config
from core.models import PhoneMetadata, ProviderResult


class BaseProvider(ABC):
    #: Unique lowercase identifier used by --provider and in reports.
    name: str = "base"

    def __init__(self, config: Config) -> None:
        self.config = config

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True when required credentials are present."""

    @abstractmethod
    def lookup(self, meta: PhoneMetadata) -> ProviderResult:
        """Query the service. Must not raise for expected failures."""
