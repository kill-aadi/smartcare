from io import StringIO

import pytest
from django.core.management import call_command

from accounts.models import Role, User
from doctors.models import Doctor, Specialization
from hospitals.models import ApprovalStatus, Hospital
from pharmacy.models import Pharmacy

KNOWN_LOGINS = {
    "admin@smartcare.test": Role.ADMIN,
    "hospital@smartcare.test": Role.HOSPITAL,
    "pending-hospital@smartcare.test": Role.HOSPITAL,
    "doctor@smartcare.test": Role.DOCTOR,
    "pharmacy@smartcare.test": Role.PHARMACY,
    "patient@smartcare.test": Role.PATIENT,
}


def seed(*args) -> str:
    out = StringIO()
    call_command("seed_demo", *args, stdout=out)
    return out.getvalue()


def counts():
    return {
        "users": User.objects.count(),
        "approved": Hospital.objects.approved().count(),
        "pending": Hospital.objects.filter(approval_status=ApprovalStatus.PENDING).count(),
        "rejected": Hospital.objects.filter(approval_status=ApprovalStatus.REJECTED).count(),
        "doctors": Doctor.objects.count(),
        "pharmacies": Pharmacy.objects.count(),
        "patients": User.objects.filter(role=Role.PATIENT).count(),
    }


def test_seed_creates_the_documented_demo_world(db):
    seed()

    c = counts()
    assert (c["approved"], c["pending"], c["rejected"]) == (5, 1, 1)
    assert c["pharmacies"] == 5 and c["patients"] == 10
    for hospital in Hospital.objects.approved():
        assert 3 <= hospital.doctors.count() <= 4
    covered = set(Doctor.objects.values_list("specialization__name", flat=True))
    assert covered == set(Specialization.objects.values_list("name", flat=True))


def test_every_hospital_name_is_marked_demo(db):
    seed()

    assert all("Demo" in name for name in Hospital.objects.values_list("name", flat=True))


def test_all_seeded_emails_use_the_reserved_test_domain(db):
    seed()

    assert not User.objects.exclude(email__endswith="@smartcare.test").exists()


@pytest.mark.parametrize("email,role", KNOWN_LOGINS.items())
def test_known_logins_work(db, client, email, role):
    seed()

    assert client.login(email=email, password="demo-pass-123")
    assert User.objects.get(email=email).role == role


def test_demo_doctor_and_pharmacy_share_a_hospital(db):
    seed()

    doctor = Doctor.objects.get(user__email="doctor@smartcare.test")
    pharmacy = Pharmacy.objects.get(user__email="pharmacy@smartcare.test")
    assert doctor.hospital == pharmacy.hospital
    assert doctor.hospital.user.email == "hospital@smartcare.test"


def test_second_run_changes_nothing_and_explains(db):
    seed()
    before = counts()

    output = seed()

    assert "Demo data already exists. Use --flush to recreate it." in output
    assert counts() == before


def test_flush_recreates_identically(db):
    seed()
    before = counts()
    names = list(Hospital.objects.values_list("name", flat=True))
    doctors = sorted(Doctor.objects.values_list("name", flat=True))

    seed("--flush")

    assert counts() == before
    assert list(Hospital.objects.values_list("name", flat=True)) == names
    assert sorted(Doctor.objects.values_list("name", flat=True)) == doctors


def test_flush_keeps_non_demo_users(db):
    User.objects.create_user("real.admin@example.test", password="x-pass-123")
    seed()

    seed("--flush")

    assert User.objects.filter(email="real.admin@example.test").exists()
