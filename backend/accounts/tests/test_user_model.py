import pytest
from django.db import IntegrityError

from accounts.models import Role, User


def test_create_user_uses_email_and_lowercases_it(db):
    user = User.objects.create_user("Ana@Example.TEST", password="x-pass-123")

    assert user.email == "ana@example.test"
    assert user.role == Role.PATIENT
    assert user.check_password("x-pass-123")


def test_user_has_no_username_field():
    assert User.USERNAME_FIELD == "email"
    assert not hasattr(User, "username") or User.username is None


def test_email_unique_case_insensitive(db):
    User.objects.create_user("ana@example.test", password="x-pass-123")

    with pytest.raises(IntegrityError):
        # bypass the manager's lower-casing to prove the DB constraint itself holds
        User.objects.create(email="ANA@example.test")


def test_create_superuser_is_admin_role(db):
    admin = User.objects.create_superuser("root@example.test", password="x-pass-123")

    assert admin.role == Role.ADMIN
    assert admin.is_staff
    assert admin.is_superuser


def test_login_is_case_insensitive(db, client):
    User.objects.create_user("ana@example.test", password="x-pass-123")

    assert client.login(email="ANA@EXAMPLE.TEST", password="x-pass-123")
