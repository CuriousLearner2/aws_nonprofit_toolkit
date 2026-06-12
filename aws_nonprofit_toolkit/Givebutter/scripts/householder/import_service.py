"""
Import Service - Orchestrates import data for /imports screen.

The service layer provides a stable interface that routes depend on.
Routes call service functions; service functions call repositories.
This allows repository implementations to change (fixtures → database)
without changing routes or templates.

Phase 1B-Step 5J: Wired to use repository provider for flexible repository selection.
"""

from typing import List, Dict, Any, Optional, Mapping

from .repository_provider import get_import_repository
from .service_contracts import ImportSummary


def get_imports(config: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Get list of imports for /imports screen.

    Returns list of dicts suitable for direct template rendering.
    Hides repository and view-model details from routes.

    Args:
        config: Optional configuration mapping for repository selection.
               If None, defaults to FixtureImportRepository (fixture-backed).
               Can specify {'HOUSEHOLDER_REPOSITORY': 'database', 'GIVEBUTTER_DATABASE_URL': <url>}
               for database-backed imports.

    Returns:
        List of dicts with keys: id, filename, record_count, status,
        progress, uploaded_timestamp

    Raises:
        ValueError: If database mode requested without required configuration.
    """
    repository = get_import_repository(config)
    summaries = repository.list_imports()
    return [summary.to_template_dict() for summary in summaries]
