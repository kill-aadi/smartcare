import pytest


@pytest.fixture(autouse=True)
def _media_in_tmp(settings, tmp_path):
    """Uploaded files in tests go to a throwaway folder, never the dev media volume."""
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture(autouse=True)
def _fast_password_hashing(settings):
    """Real hashing is deliberately slow; tests only need it to round-trip."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
