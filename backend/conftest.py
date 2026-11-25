import pytest


@pytest.fixture(autouse=True)
def _media_in_tmp(settings, tmp_path):
    """Uploaded files in tests go to a throwaway folder, never the dev media volume."""
    settings.MEDIA_ROOT = tmp_path / "media"
