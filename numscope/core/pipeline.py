"""Shared scan pipeline used by both the CLI and the web app."""
from __future__ import annotations

import logging
from typing import List, Optional, Sequence

from core.analyzer import PhoneAnalyzer
from core.models import PhoneMetadata, ProviderResult, ScanReport
from modules.dorks import DorkGenerator
from modules.providers.base import BaseProvider
from modules.risk import RiskScorer

log = logging.getLogger(__name__)


def safe_lookup(provider: BaseProvider, meta: PhoneMetadata) -> ProviderResult:
    try:
        return provider.lookup(meta)
    except Exception as exc:  # noqa: BLE001 - plugins must never crash us
        log.debug("provider failure", exc_info=True)
        return ProviderResult(provider.name, False,
                              error=f"unexpected {type(exc).__name__}")


def scan(raw: str, analyzer: PhoneAnalyzer, scorer: RiskScorer,
         providers: Sequence[BaseProvider], categories: Optional[List[str]],
         run_dorks: bool = True, run_risk: bool = True) -> ScanReport:
    meta = analyzer.analyze(raw)
    dorks = DorkGenerator(meta).generate(categories) if run_dorks else []

    results: List[ProviderResult] = []
    for provider in providers:
        if not meta.is_possible:
            results.append(ProviderResult(
                provider.name, False,
                error="skipped: offline check says number is not possible"))
        else:
            results.append(safe_lookup(provider, meta))

    risk = scorer.assess(meta, results) if run_risk else None
    return ScanReport(meta, dorks, risk, results)
