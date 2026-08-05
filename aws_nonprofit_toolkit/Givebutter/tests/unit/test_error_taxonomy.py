from sqlalchemy.exc import OperationalError

from scripts.householder.error_taxonomy import ErrorCategory, classify_error
from scripts.householder.http_error_adapter import adapt_error


def test_classifies_domain_and_transport_failures():
    assert classify_error(ValueError("bad input")).category is ErrorCategory.VALIDATION
    assert classify_error(ValueError("bad approval"), domain="approval").category is ErrorCategory.APPROVAL
    assert classify_error(RuntimeError("export broke"), domain="export").status_code == 500
    assert classify_error(OperationalError("select", {}, Exception())).status_code == 503
    assert classify_error(OSError("disk")).category is ErrorCategory.FILE
    assert classify_error(RuntimeError("boom")).category is ErrorCategory.UNEXPECTED


def test_adapter_is_safe_and_keeps_route_extensions():
    logged = []

    class Logger:
        def log(self, level, message, error, extra):
            logged.append(extra["request_correlation_id"])

    body, status = adapt_error(
        ValueError("invalid email"), response_factory=lambda value: value,
        logger=Logger(), extensions={"success": False}, context={"route": "validation"},
    )
    assert status == 400
    assert body == {"error": "invalid email", "success": False}
    assert len(logged) == 1 and logged[0]
    assert "invalid email" in body["error"]


def test_unexpected_adapter_never_leaks_exception_text():
    body, status = adapt_error(RuntimeError("secret stack detail"), response_factory=lambda value: value)
    assert status == 500
    assert body == {"error": "An unexpected error occurred"}
