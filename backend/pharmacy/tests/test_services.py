import pytest

from accounts.models import Role
from core.factories import HospitalFactory
from hospitals.models import ApprovalStatus
from hospitals.services import HospitalNotApproved
from pharmacy.models import Pharmacy
from pharmacy.services import create_pharmacy


def test_approved_hospital_creates_pharmacy_with_pharmacy_login(db):
    hospital = HospitalFactory()

    pharmacy = create_pharmacy(
        hospital,
        email="Rx@Care.test",
        password="a-long-pass-123",
        name="Ward Pharmacy",
        phone="0487 333 3333",
    )

    assert pharmacy.hospital == hospital
    assert pharmacy.user.role == Role.PHARMACY
    assert pharmacy.email == "rx@care.test"


def test_pending_hospital_cannot_create_pharmacy(db):
    with pytest.raises(HospitalNotApproved):
        create_pharmacy(
            HospitalFactory(approval_status=ApprovalStatus.PENDING),
            email="rx@care.test",
            password="a-long-pass-123",
            name="P",
            phone="1",
        )

    assert not Pharmacy.objects.exists()
