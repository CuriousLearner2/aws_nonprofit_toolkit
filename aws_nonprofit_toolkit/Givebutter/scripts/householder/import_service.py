"""
Import Service - Orchestrates import data for /imports screen.

The service layer provides a stable interface that routes depend on.
Routes call service functions; service functions call repositories.
This allows repository implementations to change (fixtures → database)
without changing routes or templates.
"""

from typing import List, Dict, Any

from .fixture_repository import FixtureImportRepository
from .service_contracts import ImportSummary


def get_imports() -> List[Dict[str, Any]]:
    """
    Get list of imports for /imports screen.

    Returns list of dicts suitable for direct template rendering.
    Hides repository and view-model details from routes.

    Returns:
        List of dicts with keys: id, filename, record_count, status,
        progress, uploaded_timestamp
    """
    summaries = FixtureImportRepository.list_imports()
    return [summary.to_template_dict() for summary in summaries]
