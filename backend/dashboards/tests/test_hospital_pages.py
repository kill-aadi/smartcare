import pytest

from accounts.models import User
from core.factories import DoctorFactory, HospitalFactory, PharmacyFactory, SpecializationFactory
from doctors.models import Doctor
from hospitals.models import ApprovalStatus
from pharmacy.models import Pharmacy


@pytest.fixture
def hospital(db):
    return HospitalFactory()


@pytest.fixture
def hospital_client(client, hospital):
    client.force_login(hospital.user)
    return client


def _doctor_data(**overrides):
    return {
        "email": "new.doc@care.test",
        "password1": "a-long-pass-123",
        "password2": "a-long-pass-123",
        "name": "Dr Fictional",
        "specialization": SpecializationFactory(name="Cardiology").pk,
        "qualification": "MBBS",
        "experience_years": 4,
        "gender": "female",
    } | overrides


def test_doctor_list_shows_only_own_doctors(hospital_client, hospital):
    DoctorFactory(hospital=hospital, name="Dr Mine")
    DoctorFactory(name="Dr Someone Else")

    response = hospital_client.get("/dashboard/hospital/doctors/")

    assert b"Dr Mine" in response.content
    assert b"Dr Someone Else" not in response.content


def test_add_doctor(hospital_client, hospital):
    response = hospital_client.post("/dashboard/hospital/doctors/new/", _doctor_data())

    assert response.status_code == 302
    assert Doctor.objects.get().hospital == hospital


def test_duplicate_email_shows_form_error_and_creates_no_user(hospital_client):
    DoctorFactory(user__email="taken@care.test")
    users_before = User.objects.count()

    response = hospital_client.post(
        "/dashboard/hospital/doctors/new/", _doctor_data(email="TAKEN@care.test")
    )

    assert response.status_code == 200
    assert b"A user with that email already exists." in response.content
    assert User.objects.count() == users_before


def test_edit_own_doctor(hospital_client, hospital):
    doctor = DoctorFactory(hospital=hospital)
    data = {
        "name": "Dr Renamed",
        "specialization": doctor.specialization.pk,
        "qualification": "MBBS, MS",
        "experience_years": 9,
        "gender": "male",
    }

    hospital_client.post(f"/dashboard/hospital/doctors/{doctor.pk}/", data)

    doctor.refresh_from_db()
    assert doctor.name == "Dr Renamed"


def test_other_hospitals_doctor_is_404(hospital_client):
    other = DoctorFactory()

    assert hospital_client.get(f"/dashboard/hospital/doctors/{other.pk}/").status_code == 404
    assert (
        hospital_client.post(f"/dashboard/hospital/doctors/{other.pk}/active/").status_code == 404
    )


def test_toggle_doctor_active(hospital_client, hospital):
    doctor = DoctorFactory(hospital=hospital)

    hospital_client.post(f"/dashboard/hospital/doctors/{doctor.pk}/active/")

    doctor.user.refresh_from_db()
    assert doctor.user.is_active is False


def test_pharmacies_add_and_list(hospital_client, hospital):
    PharmacyFactory(name="Someone Else's Pharmacy")

    hospital_client.post(
        "/dashboard/hospital/pharmacies/new/",
        {
            "email": "rx@care.test",
            "password1": "a-long-pass-123",
            "password2": "a-long-pass-123",
            "name": "Ward Pharmacy",
            "phone": "0487 333 3333",
        },
    )
    response = hospital_client.get("/dashboard/hospital/pharmacies/")

    assert Pharmacy.objects.get(hospital=hospital).name == "Ward Pharmacy"
    assert b"Ward Pharmacy" in response.content
    assert b"Someone Else" not in response.content


@pytest.mark.parametrize(
    "url", ["/dashboard/hospital/doctors/new/", "/dashboard/hospital/pharmacies/new/"]
)
def test_pending_hospital_cannot_open_add_pages(db, client, url):
    client.force_login(HospitalFactory(approval_status=ApprovalStatus.PENDING).user)

    response = client.post(url, {})

    assert response.status_code == 302
    assert response.url == "/dashboard/pending/"
