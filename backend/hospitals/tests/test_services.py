from decimal import Decimal

import pytest
from django.core import mail
from django.core.files.base import ContentFile

from accounts.models import Role
from core.exceptions import InvalidTransition, NotAllowed
from core.factories import HospitalFactory, UserFactory
from hospitals.models import ApprovalStatus
from hospitals.services import (
    ReasonRequired,
    approve_hospital,
    register_hospital,
    reject_hospital,
)


@pytest.fixture
def admin(db):
    return UserFactory(role=Role.ADMIN)


def _register(**overrides):
    data = dict(
        email="New@Care.TEST",
        password="a-long-pass-123",
        name="Fictional Care",
        place="Irinjalakuda",
        phone="0480 000 0000",
        latitude=Decimal("10.343000"),
        longitude=Decimal("76.211000"),
        licence_proof=ContentFile(b"%PDF-1.4", name="licence.pdf"),
    )
    return register_hospital(**(data | overrides))


def test_register_creates_pending_hospital_with_hospital_role_user(db):
    hospital = _register()

    assert hospital.approval_status == ApprovalStatus.PENDING
    assert hospital.user.role == Role.HOSPITAL
    assert hospital.user.email == "new@care.test"
    assert hospital.email == "new@care.test"
    assert hospital.user.check_password("a-long-pass-123")
    assert hospital.licence_proof.name.startswith("licences/")


def test_approve_sets_status_and_reviewed_at_and_emails(admin):
    hospital = HospitalFactory(approval_status=ApprovalStatus.PENDING)

    approve_hospital(hospital, by=admin)

    hospital.refresh_from_db()
    assert hospital.approval_status == ApprovalStatus.APPROVED
    assert hospital.reviewed_at is not None
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [hospital.email]


def test_reject_records_reason(admin):
    hospital = HospitalFactory(approval_status=ApprovalStatus.PENDING)

    reject_hospital(hospital, by=admin, reason="Licence is unreadable")

    hospital.refresh_from_db()
    assert hospital.approval_status == ApprovalStatus.REJECTED
    assert hospital.rejection_reason == "Licence is unreadable"
    assert len(mail.outbox) == 1


def test_reject_requires_non_empty_reason(admin):
    hospital = HospitalFactory(approval_status=ApprovalStatus.PENDING)

    with pytest.raises(ReasonRequired):
        reject_hospital(hospital, by=admin, reason="   ")


def test_rejected_hospital_can_later_be_approved(admin):
    hospital = HospitalFactory(approval_status=ApprovalStatus.REJECTED)

    approve_hospital(hospital, by=admin)

    assert hospital.approval_status == ApprovalStatus.APPROVED


def test_approving_an_approved_hospital_is_invalid(admin):
    with pytest.raises(InvalidTransition):
        approve_hospital(HospitalFactory(), by=admin)


def test_approved_hospital_cannot_be_rejected(admin):
    with pytest.raises(InvalidTransition):
        reject_hospital(HospitalFactory(), by=admin, reason="x")


@pytest.mark.parametrize("role", [Role.HOSPITAL, Role.DOCTOR, Role.PHARMACY, Role.PATIENT])
def test_only_admins_can_review(db, role):
    hospital = HospitalFactory(approval_status=ApprovalStatus.PENDING)

    with pytest.raises(NotAllowed):
        approve_hospital(hospital, by=UserFactory(role=role))
    with pytest.raises(NotAllowed):
        reject_hospital(hospital, by=UserFactory(role=role), reason="x")
