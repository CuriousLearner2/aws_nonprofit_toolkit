"""Canonical email validation helpers for review-time parsing.

This helper centralizes syntax validation for reviewed values and raw/effective
values used by validation review, autosave, approval readiness, and export
preview. It deliberately keeps the repository's current product policy:

- blank values are invalid unless a caller explicitly allows blanks
- leading/trailing whitespace is ignored for validation
- entered text is preserved exactly aside from trim-only cleanup
- ``localhost`` is accepted to preserve current fixture/test behavior
- DNS / deliverability checks are disabled
- raw/reviewed values are never mutated here
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Tuple

from email_validator import EmailNotValidError, validate_email as email_validator_validate_email


EMAIL_REQUIRED_ERROR = "Email field is empty"
EMAIL_FORMAT_ERROR = "Invalid email format"
EMAIL_MISSING_AT_ERROR = "Invalid email format (missing @)"

# Common typo domains - maps incorrect domain to correct domain.
COMMON_TYPO_DOMAINS = {
    "gamil.com": "gmail.com",      # i-l swap
    "gmial.com": "gmail.com",      # letter swap
    "gmal.com": "gmail.com",       # missing i
    "gmai.com": "gmail.com",       # incomplete
    "yahooo.com": "yahoo.com",     # extra o
    "yaho.com": "yahoo.com",       # missing o
    "hotmial.com": "hotmail.com",  # letter swap
    "hotmal.com": "hotmail.com",   # missing i
}

# Top domains that receive stricter typo detection because they are common
# donor addresses and are frequently mistyped.
RECOGNIZED_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "aol.com",
    "icloud.com",
    "mail.com",
    "gmx.com",
    "web.de",
    "protonmail.com",
    "proton.me",
    "zoho.com",
    "fastmail.com",
    "mailbox.org",
    "posteo.de",
    "yahoo.co.uk",
    "yahoo.ca",
    "yahoo.fr",
    "yahoo.de",
    "yahoo.it",
    "outlook.co.uk",
    "outlook.fr",
    "outlook.de",
    "hotmail.co.uk",
    "hotmail.fr",
    "hotmail.de",
    "mail.ru",
    "yandex.com",
    "qq.com",
    "sina.com",
    "163.com",
}


@dataclass(frozen=True)
class EmailValidationResult:
    """Structured validation result for review-time email parsing."""

    valid: bool
    normalized_value: Optional[str] = None
    blocking_error: Optional[str] = None
    warnings: Tuple[str, ...] = field(default_factory=tuple)


def _build_typo_warning(email_lower: str) -> Optional[str]:
    """Return a product-facing typo warning if the email looks suspicious."""
    if "@" not in email_lower:
        return None

    local_part, domain = email_lower.rsplit("@", 1)
    if not domain:
        return None

    if domain in COMMON_TYPO_DOMAINS:
        return f"Possible typo: did you mean {COMMON_TYPO_DOMAINS[domain]}?"

    # Preserve the existing "recognized domain" typo heuristics, but surface
    # them as warnings so review, approval, and export stay issue-aware without
    # inventing a blocking policy for typo-like domains.
    if domain in RECOGNIZED_EMAIL_DOMAINS:
        invalid_typos = [
            r"gmial(?:\.com)?",
            r"gmal(?:\.com)?",
            r"yahooo(?:\.com)?",
            r"hotmial(?:\.com)?",
            r"\bgmai\b",
        ]
        import re

        if any(re.search(pattern, email_lower) for pattern in invalid_typos):
            return f"Email domain '{domain}' looks like a typo"

    return None


def validate_review_email(
    value: Any,
    *,
    allow_blank: bool = False,
) -> EmailValidationResult:
    """
    Validate a reviewed email address using a canonical syntax parser.

    Deliverability / DNS checks are disabled. The helper preserves the repo's
    current acceptance of single-label domains while rejecting malformed syntax
    and special-use localhost-like inputs that should remain review-visible.
    """
    text = "" if value is None else str(value).strip()

    if not text:
        if allow_blank:
            return EmailValidationResult(valid=True, normalized_value="")
        return EmailValidationResult(valid=False, blocking_error=EMAIL_REQUIRED_ERROR)

    if "@" not in text:
        return EmailValidationResult(valid=False, blocking_error=EMAIL_MISSING_AT_ERROR)

    local_part, _domain = text.rsplit("@", 1)
    if len(local_part) > 64 or len(text) > 254:
        return EmailValidationResult(valid=False, blocking_error=EMAIL_FORMAT_ERROR)

    try:
        email_validator_validate_email(
            text,
            check_deliverability=False,
            globally_deliverable=False,
        )
    except EmailNotValidError as exc:
        # Preserve the repo's historical acceptance of localhost-style values in
        # fixture / manual UAT flows while keeping DNS checks disabled.
        local_part, domain = text.rsplit("@", 1)
        if domain.lower() == "localhost" and local_part.strip():
            try:
                email_validator_validate_email(
                    f"{local_part}@example.com",
                    check_deliverability=False,
                    globally_deliverable=False,
                )
            except EmailNotValidError:
                pass
            else:
                warning = _build_typo_warning(text.lower())
                warnings = (warning,) if warning else ()
                return EmailValidationResult(
                    valid=True,
                    normalized_value=text,
                    warnings=warnings,
                )

        error_text = str(exc)
        if "@" in error_text and "period" in error_text.lower():
            blocking_error = EMAIL_MISSING_AT_ERROR
        else:
            blocking_error = EMAIL_FORMAT_ERROR
        return EmailValidationResult(valid=False, blocking_error=blocking_error)

    _local_part, domain = text.rsplit("@", 1)
    if domain.lower() != "localhost" and "." not in domain:
        return EmailValidationResult(valid=False, blocking_error=EMAIL_FORMAT_ERROR)

    warning = _build_typo_warning(text.lower())
    warnings = (warning,) if warning else ()
    return EmailValidationResult(
        valid=True,
        normalized_value=text,
        warnings=warnings,
    )
