"""Canonical phonenumbers-backed phone validation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import phonenumbers


DEFAULT_PHONE_REGION = "US"
PHONE_REQUIRED_ERROR = "Phone number is empty"
PHONE_FORMAT_ERROR = "Invalid phone format"


@dataclass(frozen=True)
class PhoneValidationResult:
    """Structured validation result for review-time phone parsing."""

    valid: bool
    normalized_value: Optional[str] = None
    blocking_error: Optional[str] = None
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    formatted: Optional[str] = None
    national: Optional[str] = None
    international: Optional[str] = None
    country_code: Optional[int] = None
    region: Optional[str] = None
    number_type: Optional[str] = None


def _phone_type_name(parsed: phonenumbers.PhoneNumber) -> str:
    """Return a stable product-facing number type label."""
    number_type = phonenumbers.number_type(parsed)
    type_map = {
        phonenumbers.PhoneNumberType.FIXED_LINE: "FIXED_LINE",
        phonenumbers.PhoneNumberType.MOBILE: "MOBILE",
        phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "FIXED_LINE_OR_MOBILE",
        phonenumbers.PhoneNumberType.TOLL_FREE: "TOLL_FREE",
        phonenumbers.PhoneNumberType.PREMIUM_RATE: "PREMIUM_RATE",
        phonenumbers.PhoneNumberType.SHARED_COST: "SHARED_COST",
        phonenumbers.PhoneNumberType.VOIP: "VOIP",
        phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "PERSONAL_NUMBER",
        phonenumbers.PhoneNumberType.PAGER: "PAGER",
        phonenumbers.PhoneNumberType.UAN: "UAN",
        phonenumbers.PhoneNumberType.VOICEMAIL: "VOICEMAIL",
        phonenumbers.PhoneNumberType.UNKNOWN: "UNKNOWN",
    }
    return type_map.get(number_type, "UNKNOWN")


def validate_review_phone(
    value: Any,
    *,
    allow_blank: bool = False,
    default_region: str = DEFAULT_PHONE_REGION,
) -> PhoneValidationResult:
    """
    Validate a reviewed phone number using phonenumbers.

    The canonical policy preserves the repo's accepted North American
    formatting flexibility while enforcing exactly 10 national digits for
    domestic numbers:
    - numbers are parsed from the original string
    - default region is US when no country code is present
    - +1 / leading 1 domestic formats are accepted
    - parsed values must have country code 1 and a 10-digit national number
    - parse failures, missing digits, extra digits, and extensions are blocking
    - whitespace is trimmed for validation only
    - the reviewed string itself is preserved by callers
    """
    text = "" if value is None else str(value).strip()

    if not text:
        if allow_blank:
            return PhoneValidationResult(valid=True, normalized_value="")
        return PhoneValidationResult(valid=False, blocking_error=PHONE_REQUIRED_ERROR)

    try:
        parsed = phonenumbers.parse(text, default_region)
    except phonenumbers.NumberParseException:
        return PhoneValidationResult(valid=False, blocking_error=PHONE_FORMAT_ERROR)

    national_digits = str(parsed.national_number)
    if parsed.country_code != 1:
        return PhoneValidationResult(valid=False, blocking_error=PHONE_FORMAT_ERROR)

    if len(national_digits) != 10:
        return PhoneValidationResult(valid=False, blocking_error=PHONE_FORMAT_ERROR)

    if parsed.extension:
        return PhoneValidationResult(valid=False, blocking_error=PHONE_FORMAT_ERROR)

    return PhoneValidationResult(
        valid=True,
        normalized_value=text,
        formatted=phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
        national=phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
        international=phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
        country_code=parsed.country_code,
        region=phonenumbers.region_code_for_number(parsed),
        number_type=_phone_type_name(parsed),
    )


def validate_phone(
    phone_number: str,
    country: str = DEFAULT_PHONE_REGION,
) -> Dict[str, Any]:
    """
    Backwards-compatible dictionary wrapper around validate_review_phone().
    """
    result = validate_review_phone(phone_number, allow_blank=False, default_region=country)
    payload: Dict[str, Any] = {
        "valid": result.valid,
        "formatted": result.formatted,
        "national": result.national,
        "international": result.international,
        "country_code": result.country_code,
        "region": result.region,
        "number_type": result.number_type,
    }
    if not result.valid:
        payload["error"] = result.blocking_error or PHONE_FORMAT_ERROR
    else:
        payload["normalized_value"] = result.normalized_value
    return payload


def is_valid_phone(phone_number: str, country: str = DEFAULT_PHONE_REGION) -> bool:
    """
    Simple boolean check for phone validity.
    """
    return validate_review_phone(
        phone_number,
        allow_blank=False,
        default_region=country,
    ).valid


def format_phone(
    phone_number: str,
    country: str = DEFAULT_PHONE_REGION,
    format_type: str = "E164",
) -> Optional[str]:
    """
    Format a valid phone number to a specific format.
    """
    result = validate_review_phone(phone_number, allow_blank=False, default_region=country)
    if not result.valid:
        return None

    try:
        parsed = phonenumbers.parse(result.normalized_value or str(phone_number).strip(), country)
        format_map = {
            "E164": phonenumbers.PhoneNumberFormat.E164,
            "INTERNATIONAL": phonenumbers.PhoneNumberFormat.INTERNATIONAL,
            "NATIONAL": phonenumbers.PhoneNumberFormat.NATIONAL,
            "RFC3966": phonenumbers.PhoneNumberFormat.RFC3966,
        }
        fmt = format_map.get(format_type, phonenumbers.PhoneNumberFormat.E164)
        return phonenumbers.format_number(parsed, fmt)
    except Exception:
        return None
