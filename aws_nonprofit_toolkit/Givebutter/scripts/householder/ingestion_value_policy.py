"""Legacy normalization policy used during CSV ingestion."""

import math
import numbers


def normalize_ingestion_scalar(value):
    """Convert missing scalar values to empty text without changing numbers."""
    if value is None:
        return ""
    if isinstance(value, numbers.Real) and math.isnan(value):
        return ""
    return value


def split_name(name):
    name = normalize_ingestion_scalar(name)
    if not isinstance(name, str):
        name = str(name)
    if not name or not name.strip():
        return (None, None)
    parts = name.strip().split()
    return (parts[0], " ".join(parts[1:]) or None)


def extract_digits_from_phone(phone):
    if not phone or not str(phone).strip():
        return ""
    return "".join(c for c in str(phone).strip() if c.isdigit())


def parse_amount(amount_str):
    if not amount_str or not str(amount_str).strip():
        return None
    try:
        return float(str(amount_str).strip().replace("$", "").replace(",", "").strip())
    except ValueError:
        return None
