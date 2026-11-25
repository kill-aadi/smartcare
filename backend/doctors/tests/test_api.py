import pytest
from rest_framework.test import APIClient

from core.factories import DoctorFactory, HospitalFactory, PatientFactory, SpecializationFactory
from hospitals.models import ApprovalStatus


@pytest.fixture
def api(db):
    client = APIClient()
    client.force_authenticate(PatientFactory())
    return client


def test_specializations_list(api):
    response = api.get("/api/specializations/")

    assert response.status_code == 200
    assert len(response.data) == 12
    assert set(response.data[0]) == {"id", "name", "description"}


def test_doctors_hide_pending_rejected_and_inactive(api):
    visible = DoctorFactory()
    DoctorFactory(hospital=HospitalFactory(approval_status=ApprovalStatus.PENDING))
    DoctorFactory(hospital=HospitalFactory(approval_status=ApprovalStatus.REJECTED))
    DoctorFactory(user__is_active=False)

    response = api.get("/api/doctors/")

    assert [d["id"] for d in response.data] == [visible.pk]


def test_doctor_item_shape(api):
    DoctorFactory()

    item = api.get("/api/doctors/").data[0]

    assert set(item) == {
        "id",
        "name",
        "specialization",
        "qualification",
        "experience_years",
        "gender",
        "photo_url",
        "hospital",
    }
    assert set(item["specialization"]) == {"id", "name"}
    assert set(item["hospital"]) == {"id", "name", "place", "latitude", "longitude"}


def test_filter_by_specialization_and_hospital(api):
    derm = SpecializationFactory(name="Dermatology")
    hospital = HospitalFactory()
    wanted = DoctorFactory(specialization=derm, hospital=hospital)
    DoctorFactory(specialization=derm)
    DoctorFactory(hospital=hospital)

    response = api.get("/api/doctors/", {"specialization": derm.pk, "hospital": hospital.pk})

    assert [d["id"] for d in response.data] == [wanted.pk]


def test_bad_filter_is_400(api):
    assert api.get("/api/doctors/", {"specialization": "abc"}).status_code == 400
