import pytest

from accounts.models import Gender, Role
from core.exceptions import NotAllowed
from core.factories import DoctorFactory, HospitalFactory, SpecializationFactory
from doctors.models import Doctor
from doctors.services import create_doctor, set_doctor_active
from hospitals.models import ApprovalStatus
from hospitals.services import HospitalNotApproved


def _create(hospital, **overrides):
    data = dict(
        email="Dr.New@Care.TEST",
        password="a-long-pass-123",
        name="Dr Fictional",
        specialization=SpecializationFactory(name="Dermatology"),
        qualification="MBBS, MD",
        experience_years=7,
        gender=Gender.MALE,
    )
    return create_doctor(hospital, **(data | overrides))


def test_approved_hospital_creates_doctor_with_doctor_login(db):
    hospital = HospitalFactory()

    doctor = _create(hospital)

    assert doctor.hospital == hospital
    assert doctor.user.role == Role.DOCTOR
    assert doctor.user.email == "dr.new@care.test"
    assert doctor.user.check_password("a-long-pass-123")


@pytest.mark.parametrize("status", [ApprovalStatus.PENDING, ApprovalStatus.REJECTED])
def test_unapproved_hospital_cannot_create_doctor(db, status):
    with pytest.raises(HospitalNotApproved):
        _create(HospitalFactory(approval_status=status))

    assert not Doctor.objects.exists()


def test_deactivated_doctor_cannot_log_in_and_is_hidden_from_patients(db, client):
    doctor = DoctorFactory(user__email="dr@example.test")

    set_doctor_active(doctor.hospital, doctor, False)

    assert not client.login(email="dr@example.test", password="x-pass-123")
    assert doctor not in Doctor.objects.visible_to_patients()

    set_doctor_active(doctor.hospital, doctor, True)
    assert client.login(email="dr@example.test", password="x-pass-123")


def test_cannot_toggle_another_hospitals_doctor(db):
    doctor = DoctorFactory()

    with pytest.raises(NotAllowed):
        set_doctor_active(HospitalFactory(), doctor, False)
