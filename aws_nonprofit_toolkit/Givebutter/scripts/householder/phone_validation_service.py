"""Canonical phonenumbers-backed phone validation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

import phonenumbers

from .phone_type_policy import phone_type_name
from .phone_format_policy import format_type_for


DEFAULT_PHONE_REGION = "US"
PHONE_REQUIRED_ERROR = "Phone number is empty"
PHONE_FORMAT_ERROR = "Invalid phone format"
PHONE_COUNTRY_CODE_WARNING = "International numbers should include a country code."
PHONE_REVIEW_WARNING = "Phone format could not be confidently verified; review before export."
PHONE_MAX_STORAGE_LENGTH = 255


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


def validate_review_phone(
    value: Any,
    *,
    allow_blank: bool = False,
    default_region: str = DEFAULT_PHONE_REGION,
) -> PhoneValidationResult:
    """
    Validate a reviewed phone number using phonenumbers.

    The canonical policy preserves the repo's accepted North American
    formatting flexibility while using libphonenumber's validity rules:
    - numbers are parsed from the original string
    - default region is US when no country code is present
    - +1 / leading 1 domestic formats are accepted
    - explicit international country codes are validated against that country
    - domestic parsing defaults to US, while valid NANP regions are accepted
    - country-less numbers that cannot be safely classified are retained with
      guidance rather than silently coerced to +1
    - phone-like parse failures, missing digits, extra digits, and extensions
      remain reviewable warnings; clearly non-phone and unsafe values block
    - whitespace is trimmed for validation only
    - the reviewed string itself is preserved by callers
    """
    if value is not None and not isinstance(value, str):
        return PhoneValidationResult(valid=False, blocking_error=PHONE_FORMAT_ERROR)

    text = "" if value is None else value.strip()

    if not text:
        if allow_blank:
            return PhoneValidationResult(valid=True, normalized_value="")
        return PhoneValidationResult(valid=False, blocking_error=PHONE_REQUIRED_ERROR)

    if len(text) > PHONE_MAX_STORAGE_LENGTH:
        return PhoneValidationResult(valid=False, blocking_error="Phone value is too long to store")

    def looks_phone_like(candidate: str) -> bool:
        digits = sum(character.isdigit() for character in candidate)
        allowed = set("0123456789+()-./ xX")
        return digits >= 3 and all(character in allowed for character in candidate)

    phone_like = looks_phone_like(text)

    try:
        parsed = phonenumbers.parse(text, default_region)
    except phonenumbers.NumberParseException:
        if phone_like:
            return PhoneValidationResult(
                valid=True,
                normalized_value=text,
                warnings=(PHONE_REVIEW_WARNING,),
            )
        return PhoneValidationResult(valid=False, blocking_error=PHONE_FORMAT_ERROR)

    if parsed.extension:
        if phone_like:
            return PhoneValidationResult(
                valid=True,
                normalized_value=text,
                warnings=(PHONE_REVIEW_WARNING,),
            )
        return PhoneValidationResult(valid=False, blocking_error=PHONE_FORMAT_ERROR)

    has_explicit_country_code = text.startswith('+') or text.startswith('00')
    if not phonenumbers.is_possible_number(parsed):
        if phone_like:
            return PhoneValidationResult(
                valid=True,
                normalized_value=text,
                warnings=(PHONE_REVIEW_WARNING,),
            )
        return PhoneValidationResult(valid=False, blocking_error=PHONE_FORMAT_ERROR)
    if not has_explicit_country_code:
        national_digits = str(parsed.national_number)
        if parsed.country_code != 1 or len(national_digits) != 10:
            # Without a country code there is no reliable way to interpret a
            # plausible international number using the US default region.
            # Keep it visible for review and require explicit country context
            # rather than silently treating it as +1.
            if 10 <= len(national_digits) <= 15 and national_digits.isdigit():
                return PhoneValidationResult(
                    valid=True,
                    normalized_value=text,
                    warnings=(PHONE_COUNTRY_CODE_WARNING,),
                )
            if phone_like:
                return PhoneValidationResult(
                    valid=True,
                    normalized_value=text,
                    warnings=(PHONE_REVIEW_WARNING,),
                )
            return PhoneValidationResult(valid=False, blocking_error=PHONE_FORMAT_ERROR)
    if has_explicit_country_code:
        if not phonenumbers.is_valid_number(parsed):
            if phone_like:
                return PhoneValidationResult(
                    valid=True,
                    normalized_value=text,
                    warnings=(PHONE_REVIEW_WARNING,),
                )
            return PhoneValidationResult(valid=False, blocking_error=PHONE_FORMAT_ERROR)

    # A number confidently parsed as NANP is a valid domestic number even
    # when the reviewer entered it without a country prefix.  Do not infer
    # international intent from ordinary US/Canada/Jamaica formatting.
    country_code_warning = (
        PHONE_COUNTRY_CODE_WARNING
        if not has_explicit_country_code and parsed.country_code != 1
        else ()
    )
    return PhoneValidationResult(
        valid=True,
        normalized_value=phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
        warnings=(country_code_warning,) if country_code_warning else (),
        formatted=phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
        national=phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
        international=phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
        country_code=parsed.country_code,
        region=phonenumbers.region_code_for_number(parsed),
        number_type=phone_type_name(parsed),
    )


def build_phone_validation_issue(value: Any) -> Optional[dict[str, str]]:
    """Project the canonical phone result into the review issue contract."""
    result = validate_review_phone(value, allow_blank=False, default_region=DEFAULT_PHONE_REGION)
    if result.warnings:
        return {
            "description": result.warnings[0],
            "severity": "warning",
            "reason": "format",
        }
    if not result.valid:
        return {
            "description": result.blocking_error or PHONE_FORMAT_ERROR,
            "severity": "error",
            "reason": "format",
        }
    return None


def validate_phone(
    phone_number: str,
    country: str = DEFAULT_PHONE_REGION,
) -> Dict[str, Any]:
    """
    Backwards-compatible dictionary wrapper around validate_review_phone().
    """
    result = validate_review_phone(phone_number, allow_blank=False, default_region=country)
    confident_valid = result.valid and PHONE_REVIEW_WARNING not in result.warnings
    payload: Dict[str, Any] = {
        "valid": confident_valid,
        "formatted": result.formatted,
        "national": result.national,
        "international": result.international,
        "country_code": result.country_code,
        "region": result.region,
        "number_type": result.number_type,
    }
    if not confident_valid:
        payload["error"] = result.blocking_error or PHONE_FORMAT_ERROR
    else:
        payload["normalized_value"] = result.normalized_value
        if result.warnings:
            payload["warnings"] = list(result.warnings)
    return payload


def is_valid_phone(phone_number: str, country: str = DEFAULT_PHONE_REGION) -> bool:
    """
    Simple boolean check for phone validity.
    """
    result = validate_review_phone(
        phone_number,
        allow_blank=False,
        default_region=country,
    )
    return result.valid and PHONE_REVIEW_WARNING not in result.warnings


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
    if result.warnings and not result.formatted:
        return None

    try:
        parsed = phonenumbers.parse(result.normalized_value or str(phone_number).strip(), country)
        return phonenumbers.format_number(parsed, format_type_for(format_type))
    except Exception:
        return None
