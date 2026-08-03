"""Pure construction of the audit payload for a completed ingestion."""


def build_ingestion_audit_details(
    *,
    filename: str,
    record_count: int,
    pass_count: int,
    warning_count: int,
    fail_count: int,
    validation_items: int,
    normalization_items: int,
) -> dict:
    """Return the stable audit details formerly assembled in the service."""
    return {
        "source": "givebutter_export",
        "filename": filename,
        "record_count": record_count,
        "validation_summary": {
            "PASS": pass_count,
            "WARNING": warning_count,
            "FAIL": fail_count,
        },
        "items_created": {
            "validation": validation_items,
            "normalization": normalization_items,
            "duplicate": 0,
            "household": 0,
        },
    }
