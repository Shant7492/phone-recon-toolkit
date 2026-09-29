"""Offline metadata extraction built on Google's libphonenumber port."""
from __future__ import annotations

import re
from typing import Optional

import phonenumbers
from phonenumbers import (
    NumberParseException,
    PhoneNumberFormat,
    PhoneNumberType,
    ValidationResult,
    carrier,
    geocoder,
    timezone,
)

from core.models import PhoneMetadata

_TYPE_NAMES = {
    value: name
    for name, value in vars(PhoneNumberType).items()
    if name.isupper() and isinstance(value, int)
}

_REASONS = {
    ValidationResult.IS_POSSIBLE: "Length matches a valid pattern",
    ValidationResult.IS_POSSIBLE_LOCAL_ONLY: (
        "Only dialable locally (missing area/trunk code)"
    ),
    ValidationResult.INVALID_COUNTRY_CODE: "Invalid country calling code",
    ValidationResult.TOO_SHORT: "Too short for this country",
    ValidationResult.TOO_LONG: "Too long for this country",
    ValidationResult.INVALID_LENGTH: (
        "Length not valid for any number type in this country"
    ),
}

_PARSE_HINTS = {
    NumberParseException.INVALID_COUNTRY_CODE: (
        "Missing or invalid country code. Use +<country code>... or pass "
        "--region (e.g. --region IN)."
    ),
    NumberParseException.NOT_A_NUMBER: "Input does not look like a phone number.",
    NumberParseException.TOO_SHORT_AFTER_IDD: (
        "Too short after the international dialing prefix."
    ),
    NumberParseException.TOO_SHORT_NSN: "National number is too short.",
    NumberParseException.TOO_LONG: "Number is too long to be valid.",
}


class PhoneAnalyzer:
    """Turn a raw string into a PhoneMetadata record without any network I/O."""

    def __init__(self, default_region: Optional[str] = None,
                 language: str = "en") -> None:
        self.default_region = default_region
        self.language = language

    def analyze(self, raw: str) -> PhoneMetadata:
        cleaned = raw.strip()
        meta = PhoneMetadata(
            raw_input=raw, parsed=False, digits=re.sub(r"\D", "", cleaned)
        )

        try:
            number = phonenumbers.parse(cleaned, self.default_region)
        except NumberParseException as exc:
            meta.parse_error = _PARSE_HINTS.get(exc.error_type, str(exc))
            no_plus = not cleaned.startswith("+")
            missing_region = (
                exc.error_type == NumberParseException.INVALID_COUNTRY_CODE
                and no_plus and not self.default_region
            )
            meta.parse_error_kind = (
                "missing_region" if missing_region else "malformed"
            )
            return meta

        meta.parsed = True
        meta.e164 = phonenumbers.format_number(number, PhoneNumberFormat.E164)
        meta.international = phonenumbers.format_number(
            number, PhoneNumberFormat.INTERNATIONAL
        )
        meta.national = phonenumbers.format_number(
            number, PhoneNumberFormat.NATIONAL
        )
        meta.rfc3966 = phonenumbers.format_number(
            number, PhoneNumberFormat.RFC3966
        )
        meta.country_code = number.country_code
        # National *significant* number keeps leading zeros (e.g. Italy).
        meta.national_number = phonenumbers.national_significant_number(number)
        meta.region_code = phonenumbers.region_code_for_number(number)

        reason = phonenumbers.is_possible_number_with_reason(number)
        meta.is_possible = phonenumbers.is_possible_number(number)
        meta.possible_reason = _REASONS.get(reason, f"Unknown ({reason})")
        meta.is_valid = phonenumbers.is_valid_number(number)

        meta.number_type = _TYPE_NAMES.get(
            phonenumbers.number_type(number), "UNKNOWN"
        )
        meta.carrier = carrier.name_for_number(number, self.language) or None
        meta.location = (
            geocoder.description_for_number(number, self.language) or None
        )
        meta.country = (
            geocoder.country_name_for_number(number, self.language) or None
        )
        meta.timezones = [
            tz for tz in timezone.time_zones_for_number(number)
            if tz != "Etc/Unknown"
        ]
        return meta
