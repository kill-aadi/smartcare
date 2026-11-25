import importlib

from core.factories import DoctorFactory, HospitalFactory
from doctors.models import Doctor, Specialization
from hospitals.models import ApprovalStatus

CANONICAL = [
    "General Physician",
    "Dermatology",
    "Pulmonology",
    "Cardiology",
    "Neurology",
    "Orthopaedics",
    "Gastroenterology",
    "Urology",
    "Endocrinology",
    "General Surgery",
    "ENT",
    "Gynaecology",
]


def test_migration_exports_canonical_names_in_order():
    migration = importlib.import_module("doctors.migrations.0002_seed_specializations")

    assert migration.NAMES == CANONICAL


def test_specializations_seeded(db):
    seeded = set(Specialization.objects.values_list("name", flat=True))

    assert set(CANONICAL) <= seeded
    assert all(s.description for s in Specialization.objects.all())


def test_visible_to_patients_excludes_pending_rejected_and_inactive(db):
    visible = DoctorFactory()
    DoctorFactory(hospital=HospitalFactory(approval_status=ApprovalStatus.PENDING))
    DoctorFactory(hospital=HospitalFactory(approval_status=ApprovalStatus.REJECTED))
    DoctorFactory(user__is_active=False)

    assert list(Doctor.objects.visible_to_patients()) == [visible]
