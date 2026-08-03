"""Filesystem safety policy for generated export downloads."""

from pathlib import Path


def validate_path_safety(file_path: str, export_dir: str) -> bool:
    """Return whether an export path is a regular file within the export directory."""
    try:
        export_path = Path(export_dir).resolve()
        file_path_resolved = Path(file_path).resolve()
        file_path_resolved.relative_to(export_path)
        return file_path_resolved.exists() and file_path_resolved.is_file()
    except (ValueError, OSError):
        return False
