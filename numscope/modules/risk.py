"""Heuristic risk scoring.

The score is an *explainable heuristic*, not a fraud verdict. Every point
is attached to a named factor so the analyst can disagree with it.
Weights are constants at the top of the file, meant to be tuned.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from core.models import (
    PhoneMetadata,
    ProviderResult,
    RiskAssessment,
    RiskFactor,
)

# --- tunable weights -------------------------------------------------------
LINE_TYPE_RULES = {
    "VOIP": (25, "VoIP range: cheap to acquire and easy to rotate."),
    "PREMIUM_RATE": (
        35, "Premium-rate range: callbacks can incur charges (fraud vector)."
    ),
    "SHARED_COST": (15, "Shared-cost service number."),
    "TOLL_FREE": (10, "Toll-free numbers are trivially rented (call centres)."),
    "UAN": (10, "Universal access number: corporate routing, not a person."),
    "PERSONAL_NUMBER": (12, "Follow-me number: forwards to a hidden target."),
    "PAGER": (8, "Pager range: rarely used by individuals today."),
    "VOICEMAIL": (15, "Voicemail-access range."),
    "UNKNOWN": (8, "Numbering plan does not classify this range."),
}

PTS_NOT_PARSEABLE = 45
PTS_NOT_POSSIBLE = 40
PTS_POSSIBLE_NOT_VALID = 30
PTS_NON_GEOGRAPHIC = 15
PTS_INTERNATIONAL = 5
PTS_CALLBACK_SCAM_PREFIX = 10
PTS_CALLBACK_SCAM_COUNTRY = 8
PTS_TOO_SHORT = 20
PTS_TOO_LONG = 25
PTS_PATTERN = 12
PTS_PROVIDER_DISAGREES = 5

# Commonly cited in one-ring / callback-scam advisories. Illustrative and
# editable: high false-positive rate, so the weights are deliberately low.
CARIBBEAN_NANP_AREA_CODES = {
    "242", "246", "264", "268", "284", "345", "441", "473", "649", "664",
    "721", "758", "767", "784", "809", "829", "849", "868", "869", "876",
}
CALLBACK_SCAM_COUNTRY_CODES = {216, 224, 232, 252}

LEVELS = ((70, "CRITICAL"), (45, "HIGH"), (20, "MEDIUM"), (0, "LOW"))


def longest_run(digits: str, step: int) -> int:
    """Longest run where each digit differs from the previous by `step`.

    step=0 finds repeats (5555555), +1 ascending (123456), -1 descending.
    """
    if not digits:
        return 0
    best = run = 1
    for prev, cur in zip(digits, digits[1:]):
        if int(cur) - int(prev) == step:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def level_for(score: int) -> str:
    for threshold, name in LEVELS:
        if score >= threshold:
            return name
    return "LOW"


class RiskScorer:
    def __init__(self, home_region: Optional[str] = None) -> None:
        self.home_region = home_region

    def assess(self, meta: PhoneMetadata,
               providers: Optional[Sequence[ProviderResult]] = None
               ) -> RiskAssessment:
        factors: List[RiskFactor] = []
        notes: List[str] = [
            "Heuristic score, not a fraud verdict. Offline data cannot see "
            "number porting or recent reassignment."
        ]

        if not meta.parsed and meta.parse_error_kind == "missing_region":
            notes.append(
                "No country code: validity, line-type and origin checks "
                "were NOT performed. Re-run with +CC... or --region."
            )
        factors += self._validity(meta)
        factors += self._line_type(meta, notes)
        factors += self._dialing(meta, notes)
        factors += self._format(meta)
        factors += self._provider_signals(meta, providers or [])

        score = min(100, sum(f.points for f in factors))
        return RiskAssessment(score, level_for(score), factors, notes)

    # -- factor groups ----------------------------------------------------
    @staticmethod
    def _validity(meta: PhoneMetadata) -> List[RiskFactor]:
        if not meta.parsed:
            if meta.parse_error_kind == "missing_region":
                # Our input problem, not evidence about the number.
                return []
            return [RiskFactor("Unparseable", PTS_NOT_PARSEABLE,
                               meta.parse_error or "Could not be parsed.")]
        if not meta.is_possible:
            return [RiskFactor("Impossible length", PTS_NOT_POSSIBLE,
                               meta.possible_reason or "Length invalid.")]
        if not meta.is_valid:
            return [RiskFactor(
                "Not a valid range", PTS_POSSIBLE_NOT_VALID,
                "Length is plausible but the prefix is not allocated "
                "in the numbering plan.")]
        return []

    @staticmethod
    def _line_type(meta: PhoneMetadata, notes: List[str]) -> List[RiskFactor]:
        if not (meta.parsed and meta.is_valid):
            return []
        if meta.number_type == "FIXED_LINE_OR_MOBILE":
            notes.append(
                "Line type is ambiguous in this numbering plan (e.g. +1), "
                "so VoIP cannot be detected offline."
            )
            return []
        rule = LINE_TYPE_RULES.get(meta.number_type)
        if rule is None:
            return []
        points, detail = rule
        return [RiskFactor(f"Line type: {meta.number_type}", points, detail)]

    def _dialing(self, meta: PhoneMetadata, notes: List[str]
                 ) -> List[RiskFactor]:
        if not meta.parsed:
            return []
        out: List[RiskFactor] = []
        if meta.region_code == "001":
            out.append(RiskFactor(
                "Non-geographic code", PTS_NON_GEOGRAPHIC,
                f"+{meta.country_code} is not tied to one country."))
        if self.home_region:
            if meta.region_code and meta.region_code != self.home_region:
                out.append(RiskFactor(
                    "International origin", PTS_INTERNATIONAL,
                    f"Number is {meta.region_code}, home region is "
                    f"{self.home_region}."))
        else:
            notes.append("Origin check skipped: pass --region to enable it.")
        nsn = meta.national_number or ""
        if meta.country_code == 1 and nsn[:3] in CARIBBEAN_NANP_AREA_CODES:
            out.append(RiskFactor(
                "Callback-scam area code", PTS_CALLBACK_SCAM_PREFIX,
                f"Area code {nsn[:3]} looks domestic to US/CA callers but "
                f"is a Caribbean range often cited in callback scams."))
        elif meta.country_code in CALLBACK_SCAM_COUNTRY_CODES:
            out.append(RiskFactor(
                "Callback-scam country", PTS_CALLBACK_SCAM_COUNTRY,
                f"+{meta.country_code} appears in public one-ring-scam "
                f"advisories (weak signal)."))
        return out

    @staticmethod
    def _format(meta: PhoneMetadata) -> List[RiskFactor]:
        out: List[RiskFactor] = []
        if not meta.parsed:
            if len(meta.digits) < 7:
                out.append(RiskFactor(
                    "Too few digits", PTS_TOO_SHORT,
                    f"{len(meta.digits)} digits; real numbers have 7+."))
            elif len(meta.digits) > 15:
                out.append(RiskFactor(
                    "Too many digits", PTS_TOO_LONG,
                    f"{len(meta.digits)} digits exceeds the E.164 maximum "
                    f"of 15."))
        target = meta.national_number if meta.parsed else meta.digits
        target = target or ""
        if len(target) >= 7:
            hits = []
            if longest_run(target, 0) >= 6:
                hits.append("repeated digit run")
            if longest_run(target, 1) >= 6 or longest_run(target, -1) >= 6:
                hits.append("sequential digit run")
            if len(set(target)) <= 2:
                hits.append("only 1-2 distinct digits")
            if hits:
                out.append(RiskFactor(
                    "Synthetic-looking pattern", PTS_PATTERN,
                    "; ".join(hits) + " (vanity numbers can trigger this)."))
        return out

    @staticmethod
    def _provider_signals(meta: PhoneMetadata,
                          providers: Sequence[ProviderResult]
                          ) -> List[RiskFactor]:
        out: List[RiskFactor] = []
        for res in providers:
            if res.ok and res.data.get("valid") is False and meta.is_valid:
                out.append(RiskFactor(
                    f"{res.provider} disagrees", PTS_PROVIDER_DISAGREES,
                    "Offline check says valid; provider says invalid."))
        return out
