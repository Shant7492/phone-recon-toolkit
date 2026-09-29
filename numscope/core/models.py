"""Shared data structures used across numscope."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

SEARCH_ENDPOINTS: Dict[str, str] = {
    "google": "https://www.google.com/search?q=",
    "duckduckgo": "https://duckduckgo.com/?q=",
    "bing": "https://www.bing.com/search?q=",
}

ENGINE_LABELS: Dict[str, str] = {
    "google": "Google",
    "duckduckgo": "DuckDuckGo",
    "bing": "Bing",
}


@dataclass
class PhoneMetadata:
    """Everything derivable from the number itself, fully offline."""

    raw_input: str
    parsed: bool
    digits: str = ""
    parse_error: Optional[str] = None
    #: 'missing_region' (user input issue) or 'malformed'.
    parse_error_kind: Optional[str] = None
    e164: Optional[str] = None
    international: Optional[str] = None
    national: Optional[str] = None
    rfc3966: Optional[str] = None
    country_code: Optional[int] = None
    national_number: Optional[str] = None
    region_code: Optional[str] = None
    country: Optional[str] = None
    is_possible: bool = False
    possible_reason: Optional[str] = None
    is_valid: bool = False
    number_type: str = "UNKNOWN"
    carrier: Optional[str] = None
    location: Optional[str] = None
    timezones: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class DorkQuery:
    """A search-engine query. The string works on Google, DDG and Bing."""

    category: str
    description: str
    query: str

    def url(self, engine: str) -> str:
        return SEARCH_ENDPOINTS[engine] + quote_plus(self.query)


@dataclass
class RiskFactor:
    name: str
    points: int
    detail: str


@dataclass
class RiskAssessment:
    score: int
    level: str
    factors: List[RiskFactor] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class ProviderResult:
    provider: str
    ok: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class ScanReport:
    metadata: PhoneMetadata
    dorks: List[DorkQuery] = field(default_factory=list)
    risk: Optional[RiskAssessment] = None
    providers: List[ProviderResult] = field(default_factory=list)
