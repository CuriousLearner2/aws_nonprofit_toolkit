"""Unit tests for upload ingestion configuration resolution."""

import pytest


@pytest.mark.parametrize(
    "database_url,repository_mode,ingest_setting,expected",
    [
        (None, "database", None, False),
        ("sqlite:///tmp.db", "database", None, True),
        ("sqlite:///tmp.db", "database", "true", True),
        ("sqlite:///tmp.db", "database", "TRUE", True),
        ("sqlite:///tmp.db", "database", " true ", True),
        ("sqlite:///tmp.db", "database", "false", False),
        ("sqlite:///tmp.db", "database", " no ", False),
        ("sqlite:///tmp.db", "fixture", None, False),
        ("sqlite:///tmp.db", "fixture", "true", True),
    ],
)
def test_should_ingest_upload_matrix(database_url, repository_mode, ingest_setting, expected):
    """Database mode defaults on only when the project DB exists and no override is set."""
    import scripts.uploader.app as app_module

    assert (
        app_module._should_ingest_upload(database_url, repository_mode, ingest_setting)
        is expected
    )
