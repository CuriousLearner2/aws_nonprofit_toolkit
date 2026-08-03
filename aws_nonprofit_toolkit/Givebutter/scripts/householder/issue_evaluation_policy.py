"""Pure evaluation of newly exposed issues in effective values."""

import re
from typing import Any, Dict, List, Optional

from .amount_validation_service import validate_review_amount
from .date_validation_service import validate_review_date
from .email_validation_service import validate_review_email
from .phone_validation_service import is_valid_phone


def evaluate_effective_values(effective_values: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return the issue projection for effective values."""
    issues: List[Dict[str, Any]] = []
    if "date" in effective_values:
        result = validate_review_date(effective_values.get("date"), allow_blank=True)
        if not result.valid:
            issues.append({"field": "date", "description": result.blocking_error or "Invalid date format", "severity": "error", "is_new": True})
    if "email" in effective_values:
        result = validate_review_email(effective_values.get("email"), allow_blank=False)
        if not result.valid:
            issues.append({"field": "email", "description": result.blocking_error or "Invalid email format", "severity": "error", "is_new": True})
        elif result.warnings:
            issues.append({"field": "email", "description": result.warnings[0], "severity": "warning", "is_new": True})
    if "phone" in effective_values:
        value = effective_values.get("phone")
        phone = "" if value is None else str(value).strip()
        if not phone:
            issues.append({"field": "phone", "description": "Phone number is empty", "severity": "error", "is_new": True})
        elif not is_valid_phone(phone):
            issues.append({"field": "phone", "description": "Invalid phone format", "severity": "error", "is_new": True})
    if "amount" in effective_values and effective_values.get("amount") is not None:
        issue = _validate_amount(effective_values["amount"])
        if issue:
            issues.append(issue)
    if "address" in effective_values:
        value = effective_values.get("address")
        issue = validate_address("" if value is None else str(value).strip())
        if issue:
            issues.append(issue)
    return issues


def _validate_amount(amount: Any) -> Optional[Dict[str, Any]]:
    result = validate_review_amount(amount, allow_blank=False)
    if not result.valid:
        return {"field": "amount", "description": result.blocking_error or "Invalid amount format", "severity": "error", "is_new": True}
    return None


def validate_address(address: str) -> Optional[Dict[str, Any]]:
    if not address or not str(address).strip():
        return {"field": "address", "reason": "missing", "description": "Missing address", "severity": "warning", "is_new": True}
    normalized = " ".join(str(address).strip().split())
    if normalized.count(",") == 1:
        suffix = normalized.split(",", 1)[1].strip()
        if re.fullmatch(r"[A-Za-z .'-]+\s+[A-Z]{2}(?:\s+\d{5}(?:-\d{4})?)?", suffix):
            return {"field": "address", "reason": "malformed", "description": "Malformed address", "severity": "warning", "is_new": True}
    return None
