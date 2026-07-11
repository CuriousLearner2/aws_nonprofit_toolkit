"""Canonical amount validation helpers for review-time parsing."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Optional, Tuple


AMOUNT_REQUIRED_ERROR = "Amount field is empty"
AMOUNT_FORMAT_ERROR = "Invalid amount format"
AMOUNT_POSITIVE_ERROR = "Amount must be greater than 0"
AMOUNT_PRECISION_ERROR = "Amount must have at most 2 decimal places"


@dataclass(frozen=True)
class AmountValidationResult:
    """Structured validation result for review-time amount parsing."""

    valid: bool
    normalized_value: Optional[str] = None
    blocking_error: Optional[str] = None
    warnings: Tuple[str, ...] = field(default_factory=tuple)


def _strip_currency_text(value: Any) -> str:
    """Return trimmed amount text with currency symbols removed."""
    return "" if value is None else str(value).replace("$", "").strip()


def validate_review_amount(
    value: Any,
    *,
    allow_blank: bool = False,
    valid_range: Optional[tuple[Any, Any]] = None,
) -> AmountValidationResult:
    """
    Validate a reviewed amount using Decimal-backed syntax and range checks.

    The canonical syntax accepts only non-negative ASCII decimal strings after
    removing currency symbols/commas:
    - integers
    - one decimal place
    - two decimal places

    More than two decimal places, signs, malformed separators, and non-finite
    Decimal values are rejected.
    """
    text = "" if value is None else str(value).strip()

    if not text:
        if allow_blank:
            return AmountValidationResult(valid=True, normalized_value="")
        return AmountValidationResult(valid=False, blocking_error=AMOUNT_REQUIRED_ERROR)

    cleaned = _strip_currency_text(text)
    if not cleaned:
        return AmountValidationResult(valid=False, blocking_error=AMOUNT_REQUIRED_ERROR)

    if cleaned.startswith('-'):
        return AmountValidationResult(valid=False, blocking_error=AMOUNT_POSITIVE_ERROR)

    if cleaned.startswith('+'):
        return AmountValidationResult(valid=False, blocking_error=AMOUNT_FORMAT_ERROR)

    if cleaned.count('.') > 1:
        return AmountValidationResult(valid=False, blocking_error=AMOUNT_FORMAT_ERROR)

    if ',' in cleaned:
        grouped_pattern = re.compile(r"^[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?$")
        if not grouped_pattern.match(cleaned):
            return AmountValidationResult(valid=False, blocking_error=AMOUNT_FORMAT_ERROR)
        parsed_text = cleaned.replace(',', '')
    else:
        parsed_text = cleaned

    if '.' in parsed_text:
        whole_part, decimal_part = parsed_text.split('.', 1)
        if not whole_part and not decimal_part:
            return AmountValidationResult(valid=False, blocking_error=AMOUNT_FORMAT_ERROR)
        if whole_part and not whole_part.isdigit():
            return AmountValidationResult(valid=False, blocking_error=AMOUNT_FORMAT_ERROR)
        if decimal_part and not decimal_part.isdigit():
            return AmountValidationResult(valid=False, blocking_error=AMOUNT_FORMAT_ERROR)
        if len(decimal_part) > 2:
            return AmountValidationResult(valid=False, blocking_error=AMOUNT_PRECISION_ERROR)
    elif not parsed_text.isdigit():
        return AmountValidationResult(valid=False, blocking_error=AMOUNT_FORMAT_ERROR)

    try:
        parsed = Decimal(parsed_text)
    except (InvalidOperation, ValueError):
        return AmountValidationResult(valid=False, blocking_error=AMOUNT_FORMAT_ERROR)

    if not parsed.is_finite():
        return AmountValidationResult(valid=False, blocking_error=AMOUNT_FORMAT_ERROR)

    if parsed <= 0:
        return AmountValidationResult(valid=False, blocking_error=AMOUNT_POSITIVE_ERROR)

    normalized_value = format(parsed, 'f')
    warnings = ()

    if valid_range:
        try:
            min_value = Decimal(str(valid_range[0]))
            max_value = Decimal(str(valid_range[1]))
            if parsed < min_value:
                warnings = (f"Amount below typical range (${valid_range[0]})",)
            elif parsed > max_value:
                warnings = (f"Amount above typical range (${valid_range[1]})",)
        except Exception:
            warnings = ()

    return AmountValidationResult(
        valid=True,
        normalized_value=normalized_value,
        warnings=warnings,
    )
