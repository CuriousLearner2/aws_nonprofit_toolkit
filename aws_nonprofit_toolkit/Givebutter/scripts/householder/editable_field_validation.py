"""Canonical editable-field validation policy for autosave."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional


def validate_editable_field_values(
    corrected_values: Mapping[str, Any],
) -> tuple[bool, Optional[dict[str, str]]]:
    from .phone_validation_service import validate_review_phone
    from .date_validation_service import validate_review_date
    from .amount_validation_service import validate_review_amount
    from .email_validation_service import validate_review_email

    errors: dict[str, str] = {}

    for field, value in corrected_values.items():
        if field == "amount":
            amount_result = validate_review_amount(value, allow_blank=False)
            if not amount_result.valid:
                errors["amount"] = amount_result.blocking_error or "Invalid amount format"
            continue

        if field == "date":
            date_result = validate_review_date(value, allow_blank=True)
            if not date_result.valid:
                errors["date"] = date_result.blocking_error or "Invalid date format"
            continue

        if field == "email":
            email_result = validate_review_email(value, allow_blank=False)
            if not email_result.valid:
                errors["email"] = email_result.blocking_error or "Invalid email format"
            continue

        if field == "phone":
            if not value or not isinstance(value, str):
                continue
            value_str = value.strip()
            if not value_str:
                continue
            phone_result = validate_review_phone(value_str, allow_blank=False, default_region="US")
            if not phone_result.valid:
                errors["phone"] = phone_result.blocking_error or "Invalid phone format"
            continue

        if field == "name":
            if not isinstance(value, str) or not value.strip():
                errors["name"] = "Invalid name format"
            continue

        if field == "address":
            if not isinstance(value, str) or not value.strip():
                errors["address"] = "Invalid address format"
            continue

    return (not errors), (errors or None)
