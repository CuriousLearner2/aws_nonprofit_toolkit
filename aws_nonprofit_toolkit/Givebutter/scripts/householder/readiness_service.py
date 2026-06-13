"""
Export Readiness Service - Derives batch-level readiness from export preview.

Phase 3-Step 4A: Provides read-only export readiness dashboard.
Derives readiness directly from existing export preview service logic.
No new business rules; uses accepted preview behavior as source of truth.
"""

from dataclasses import dataclass
from typing import Optional, Mapping, Any

from .export_preview_service import build_export_preview
from .dashboard_service import get_import_dashboard


@dataclass(frozen=True)
class ExportReadinessViewModel:
    """Batch-level export readiness for dashboard display."""
    batch_id: str
    batch_filename: str
    progress_pct: int

    is_export_ready: bool
    blocker_count: int
    warning_count: int
    staged_records: int

    blockers: tuple
    warnings: tuple

    queue_status: dict

    def to_template_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "batch": {
                "id": self.batch_id,
                "filename": self.batch_filename,
                "progress": self.progress_pct,
            },
            "readiness": {
                "is_export_ready": self.is_export_ready,
                "blocker_count": self.blocker_count,
                "warning_count": self.warning_count,
                "staged_records": self.staged_records,
                "blockers": list(self.blockers),
                "warnings": list(self.warnings),
            },
            "queue_status": self.queue_status,
        }


def get_export_readiness(
    import_id: str,
    config: Optional[Mapping[str, Any]] = None,
) -> ExportReadinessViewModel:
    """
    Get export readiness status for batch.

    Derives readiness DIRECTLY from existing export preview service.
    Uses same blocker/warning logic as export preview.
    No new business rules.

    Args:
        import_id: Import batch ID
        config: Optional configuration for database selection

    Returns:
        ExportReadinessViewModel with readiness derived from preview

    Raises:
        ValueError: If batch not found or preview cannot be generated
    """
    if not config:
        config = {}

    # Get preview using existing preview service (both fixture and database modes)
    try:
        preview = build_export_preview(import_id, config=config)
    except ValueError as e:
        raise ValueError(f"Cannot determine readiness: {str(e)}")

    # Get dashboard for queue status and batch metadata
    try:
        dashboard_dict = get_import_dashboard(import_id, config=config)
    except ValueError as e:
        raise ValueError(f"Cannot load batch metadata: {str(e)}")

    # Derive readiness directly from preview (this is the source of truth)
    is_export_ready = preview.is_export_ready
    blocker_count = preview.blocked_count
    warning_count = preview.warning_count
    staged_records = preview.row_count
    blockers = preview.blockers
    warnings = preview.warnings

    return ExportReadinessViewModel(
        batch_id=import_id,
        batch_filename=dashboard_dict["batch"]["filename"],
        progress_pct=dashboard_dict["batch"]["progress"],
        is_export_ready=is_export_ready,
        blocker_count=blocker_count,
        warning_count=warning_count,
        staged_records=staged_records,
        blockers=blockers,
        warnings=warnings,
        queue_status=dashboard_dict.get("queue_status", {}),
    )
