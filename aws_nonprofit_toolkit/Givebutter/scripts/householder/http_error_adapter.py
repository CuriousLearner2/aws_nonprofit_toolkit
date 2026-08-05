"""Convert classified domain failures into safe, correlated HTTP responses."""

import logging
import uuid
from collections.abc import Callable, Mapping
from typing import Any

from .error_taxonomy import classify_error


def adapt_error(error: BaseException, *, response_factory: Callable[[Mapping[str, Any]], Any],
                logger: logging.Logger | None = None, context: Mapping[str, Any] | None = None,
                extensions: Mapping[str, Any] | None = None,
                default_message: str | None = None, status_code: int | None = None,
                domain: str | None = None) -> tuple[Any, int]:
    """Build a safe JSON response while retaining route-specific extensions."""
    classified = classify_error(error, domain=domain)
    correlation_id = uuid.uuid4().hex
    use_default = default_message and classified.category.value in {"unexpected", "repository"}
    fields: dict[str, Any] = {"error": default_message if use_default else classified.message}
    if extensions:
        fields.update(dict(extensions))
    if logger:
        log_context = dict(context or {})
        log_context["request_correlation_id"] = correlation_id
        logger.log(getattr(logging, classified.log_level.upper()), "%s", error, extra=log_context)
    return response_factory(fields), status_code or classified.status_code


def adapt_http_error(*args: Any, **kwargs: Any) -> tuple[Any, int]:
    return adapt_error(*args, **kwargs)
