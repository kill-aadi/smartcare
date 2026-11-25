from decimal import Decimal

from accounts.models import Role, User
from core.factories import HospitalFactory, PatientFactory
from hospitals.models import ApprovalStatus, Hospital


def test_new_hospital_defaults_to_pending(db):
    hospital = Hospital.objects.create(
        user=User.objects.create_user("h@example.test", role=Role.HOSPITAL),
        name="Fictional Care",
        place="Chalakudy",
        phone="0480 000 0000",
        email="h@example.test",
        licence_proof="licences/x.pdf",
        latitude=Decimal("10.3"),
        longitude=Decimal("76.3"),
    )

    assert hospital.approval_status == ApprovalStatus.PENDING
    assert hospital.reviewed_at is None


def test_approved_manager(db):
    approved = HospitalFactory()
    HospitalFactory(approval_status=ApprovalStatus.PENDING)
    HospitalFactory(approval_status=ApprovalStatus.REJECTED)

    assert list(Hospital.objects.approved()) == [approved]


def test_hospital_coordinates_precision(db):
    HospitalFactory(latitude=Decimal("10.527642"), longitude=Decimal("-76.214435"))

    hospital = Hospital.objects.get()
    assert hospital.latitude == Decimal("10.527642")
    assert hospital.longitude == Decimal("-76.214435")


def test_patient_factory_returns_user_with_profile(db):
    patient = PatientFactory()

    assert patient.role == "patient"
    assert patient.patient_profile.name
