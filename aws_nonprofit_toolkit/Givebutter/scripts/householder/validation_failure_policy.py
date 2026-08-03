"""Classification of validation-service failures at the fallback boundary."""

from sqlalchemy.exc import OperationalError


def is_expected_validation_failure(error: BaseException) -> bool:
    """Return whether the caller may safely use fixture fallback data."""
    if isinstance(error, ValueError):
        return True
    return isinstance(error, OperationalError) and "no such table" in str(error).lower()
