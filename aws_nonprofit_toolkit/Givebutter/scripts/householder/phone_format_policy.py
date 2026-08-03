"""Output-format selection policy for valid phone numbers."""

import phonenumbers


def format_type_for(label: str):
    """Return the phonenumbers format constant, defaulting to E164."""
    return {
        "E164": phonenumbers.PhoneNumberFormat.E164,
        "INTERNATIONAL": phonenumbers.PhoneNumberFormat.INTERNATIONAL,
        "NATIONAL": phonenumbers.PhoneNumberFormat.NATIONAL,
        "RFC3966": phonenumbers.PhoneNumberFormat.RFC3966,
    }.get(label, phonenumbers.PhoneNumberFormat.E164)
