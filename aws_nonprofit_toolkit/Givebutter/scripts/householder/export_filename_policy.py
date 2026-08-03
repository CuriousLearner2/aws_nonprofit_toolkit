"""Filename policy for generated export files."""


def sanitize_filename(filename: str) -> str:
    """Remove unsafe path characters and leading dots from a filename stem."""
    filename = filename.replace('/', '').replace('\\', '')
    filename = filename.lstrip('.')
    return ''.join(char for char in filename if char.isalnum() or char in '-_.')


def generate_safe_filename(import_id: str, timestamp) -> str:
    """Build the stable timestamped CSV export filename."""
    sanitized_id = sanitize_filename(import_id)
    ts = timestamp.strftime('%Y%m%d_%H%M%S')
    return f"{sanitized_id}_export_{ts}.csv"
