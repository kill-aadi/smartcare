import pytest


@pytest.fixture(autouse=True)
def _media_in_tmp(settings, tmp_path):
    """Uploaded files in tests go to a throwaway folder, never the dev media volume."""
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture(autouse=True)
def _fast_password_hashing(settings):
    """Real hashing is deliberately slow; tests only need it to round-trip."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Re-create rows that data migrations add (the 12 specialisations) at the start of a run.

    A ``transaction=True`` test (the booking concurrency test) ends with a flush that deletes
    them, and ``--reuse-db`` would carry that loss into the next run. Transactional tests run
    last, so restoring once per session is enough.
    """
    from importlib import import_module

    from django.apps import apps

    with django_db_blocker.unblock():
        import_module("doctors.migrations.0002_seed_specializations").seed(apps, None)
