"""Stable domain failure taxonomy used at the Flask transport boundary."""

from dataclasses import dataclass
from enum import Enum
from sqlalchemy.exc import DBAPIError, OperationalError


class ErrorCategory(str, Enum):
    VALIDATION = "validation"
    REPOSITORY = "repository"
    APPROVAL = "approval"
    EXPORT = "export"
    FILE = "file"
    UNEXPECTED = "unexpected"


@dataclass(frozen=True)
class ClassifiedError:
    category: ErrorCategory
    status_code: int
    message: str
    log_level: str = "warning"


def classify_error(error: BaseException, *, domain: str | None = None) -> ClassifiedError:
    """Classify a domain failure without exposing exception details to clients."""
    module = type(error).__module__
    name = type(error).__name__
    if domain == "approval":
        return ClassifiedError(ErrorCategory.APPROVAL, 400 if isinstance(error, (ValueError, TypeError)) else 500,
                               str(error) if isinstance(error, (ValueError, TypeError)) else "Batch approval failed",
                               "warning" if isinstance(error, (ValueError, TypeError)) else "error")
    if domain == "export":
        return ClassifiedError(ErrorCategory.EXPORT, 400 if isinstance(error, ValueError) else 500,
                               str(error) if isinstance(error, ValueError) else "Export operation failed",
                               "warning" if isinstance(error, ValueError) else "error")
    if name in {"ExportBlockedError", "ExportUnresolvedHouseholdWarningError",
                "ExportUnresolvedDuplicateWarningError", "ExportUnresolvedValidationWarningError",
                "ExportUnresolvedNormalizationWarningError"}:
        return ClassifiedError(ErrorCategory.EXPORT, 400, str(error))
    if name in {"ExportNotFoundError", "ExportPathError"}:
        return ClassifiedError(ErrorCategory.FILE, 404, "File not found")
    if name == "ExportAccessError":
        return ClassifiedError(ErrorCategory.FILE, 403, "Access denied")
    if "export" in module or name.startswith("Export"):
        return ClassifiedError(ErrorCategory.EXPORT, 500, "Export operation failed", "error")
    if isinstance(error, LookupError):
        return ClassifiedError(ErrorCategory.REPOSITORY, 404, "Requested review item was not found")
    if isinstance(error, (ValueError, TypeError)):
        return ClassifiedError(ErrorCategory.VALIDATION, 400, str(error) or "Invalid request")
    if isinstance(error, (DBAPIError, OperationalError)):
        return ClassifiedError(ErrorCategory.REPOSITORY, 503, "Review database is unavailable", "error")
    if isinstance(error, (OSError, IOError)):
        return ClassifiedError(ErrorCategory.FILE, 500, "File operation failed", "error")
    return ClassifiedError(ErrorCategory.UNEXPECTED, 500, "An unexpected error occurred", "error")


def classify(error: BaseException, *, domain: str | None = None) -> ClassifiedError:
    return classify_error(error, domain=domain)
