"""Normalizations Service - Service layer for normalizations review route.

Thin orchestration layer that returns template-ready data for the
normalizations review screen.
"""

from typing import Dict, Any, Optional, Mapping

from .repository_provider import get_import_repository


def get_normalizations_review(
    import_id: str,
    config: Optional[Mapping[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get normalizations review page data for a specific import.

    Args:
        import_id: Import ID to fetch normalizations data for
        config: Optional configuration mapping for repository selection.

    Returns:
        Dictionary with batch and normalizations data, ready for template
    """
    repository = get_import_repository(config)

    try:
        normalizations_vm = repository.get_normalizations(import_id)
        return normalizations_vm.to_template_dict()
    except (AttributeError, NotImplementedError):
        # Fallback for when repository method isn't fully implemented
        return {
            "batch": {"id": import_id},
            "message": "Normalizations review - coming soon"
        }
