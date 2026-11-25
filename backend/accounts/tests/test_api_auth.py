import pytest
from rest_framework.test import APIClient

from accounts.models import Role, User
from core.factories import DoctorFactory, HospitalFactory, PatientFactory, UserFactory

STAFF_COPY = "This app is for patients. Staff should use the web dashboard."


@pytest.fixture
def api():
    return APIClient()


def _register(api, **overrides):
    data = {
        "email": "Asha@Example.TEST",
        "password": "a-long-pass-123",
        "name": "Asha Fictional",
        "phone": "90000 11111",
        "date_of_birth": "1998-04-02",
        "gender": "female",
        "place": "Thrissur",
    } | overrides
    return api.post("/api/auth/register/", data, format="json")


def _token(api, email, password="x-pass-123"):
    return api.post("/api/auth/token/", {"email": email, "password": password}, format="json")


def test_register_then_log_in(db, api):
    response = _register(api)

    assert response.status_code == 201
    assert response.data["email"] == "asha@example.test"
    user = User.objects.get(email="asha@example.test")
    assert user.role == Role.PATIENT
    assert user.patient_profile.name == "Asha Fictional"

    login = _token(api, "ASHA@example.test", "a-long-pass-123")
    assert login.status_code == 200
    assert {"access", "refresh"} <= set(login.data)


def test_register_existing_email_any_case_is_400(db, api):
    UserFactory(email="asha@example.test")

    response = _register(api, email="ASHA@EXAMPLE.test")

    assert response.status_code == 400
    assert "email" in response.data


def test_register_weak_password_is_400(db, api):
    response = _register(api, password="123")

    assert response.status_code == 400
    assert "password" in response.data
    assert not User.objects.exists()


def test_register_missing_name_creates_nothing(db, api):
    response = _register(api, name="")

    assert response.status_code == 400
    assert not User.objects.exists()


@pytest.mark.parametrize("make", ["doctor", "hospital", "pharmacy", "admin"])
def test_staff_cannot_get_a_token(db, api, make):
    user = {
        "doctor": lambda: DoctorFactory().user,
        "hospital": lambda: HospitalFactory().user,
        "pharmacy": lambda: UserFactory(role=Role.PHARMACY),
        "admin": lambda: UserFactory(role=Role.ADMIN),
    }[make]()

    response = _token(api, user.email)

    assert response.status_code == 401
    assert response.data["detail"] == STAFF_COPY
    assert "access" not in response.data


def test_wrong_password_is_401_without_staff_copy(db, api):
    patient = PatientFactory()

    response = _token(api, patient.email, "wrong-password")

    assert response.status_code == 401
    assert response.data["detail"] != STAFF_COPY


def test_me_returns_profile(db, api):
    patient = PatientFactory()
    access = _token(api, patient.email).data["access"]

    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = api.get("/api/me/")

    assert response.status_code == 200
    assert response.data["email"] == patient.email
    assert response.data["name"] == patient.patient_profile.name
    assert set(response.data) == {
        "id",
        "email",
        "name",
        "phone",
        "date_of_birth",
        "gender",
        "place",
    }


def test_me_with_doctor_session_is_403(db, client):
    client.force_login(DoctorFactory().user)

    assert client.get("/api/me/").status_code == 403


def test_me_without_auth_is_401(db, api):
    assert api.get("/api/me/").status_code == 401


def test_refresh_gives_new_access_token(db, api):
    refresh = _token(api, PatientFactory().email).data["refresh"]

    response = api.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")

    assert response.status_code == 200
    assert "access" in response.data


def test_refresh_fails_after_account_is_deactivated(db, api):
    patient = PatientFactory()
    refresh = _token(api, patient.email).data["refresh"]
    patient.is_active = False
    patient.save()

    response = api.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")

    assert response.status_code == 401
