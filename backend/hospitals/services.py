"""Hospital registration and the admin approval workflow."""

from decimal import Decimal

from django.core.files import File
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from accounts.models import Role, User
from core.exceptions import DomainError, InvalidTransition, NotAllowed
from hospitals.models import ApprovalStatus, Hospital


class ReasonRequired(DomainError):
    code = "reason_required"


# Which status a hospital may move to from its current one.
_ALLOWED = {
    ApprovalStatus.APPROVED: {ApprovalStatus.PENDING, ApprovalStatus.REJECTED},
    ApprovalStatus.REJECTED: {ApprovalStatus.PENDING},
}


@transaction.atomic
def register_hospital(
    *,
    email: str,
    password: str,
    name: str,
    place: str,
    phone: str,
    latitude: Decimal,
    longitude: Decimal,
    licence_proof: File,
    photo: File | None = None,
) -> Hospital:
    """Create the hospital's login and its pending registration together (both or neither)."""
    user = User.objects.create_user(email, password=password, role=Role.HOSPITAL)
    return Hospital.objects.create(
        user=user,
        name=name,
        place=place,
        phone=phone,
        email=user.email,
        latitude=latitude,
        longitude=longitude,
        licence_proof=licence_proof,
        photo=photo or "",
    )


def approve_hospital(hospital: Hospital, *, by: User) -> Hospital:
    _review(hospital, by=by, to=ApprovalStatus.APPROVED)
    _notify(hospital, "approved", "You can now log in and add your doctors and pharmacy.")
    return hospital


def reject_hospital(hospital: Hospital, *, by: User, reason: str) -> Hospital:
    reason = reason.strip()
    if not reason:
        raise ReasonRequired("Please give a reason for rejecting this hospital.")
    _review(hospital, by=by, to=ApprovalStatus.REJECTED, reason=reason)
    _notify(hospital, "rejected", f"Reason: {reason}")
    return hospital


def _review(hospital: Hospital, *, by: User, to: ApprovalStatus, reason: str = "") -> None:
    if by.role != Role.ADMIN:
        raise NotAllowed("Only an admin can review hospital registrations.")
    if hospital.approval_status not in _ALLOWED[to]:
        raise InvalidTransition(f"This hospital is already {hospital.approval_status}.")
    hospital.approval_status = to
    hospital.rejection_reason = reason
    hospital.reviewed_at = timezone.now()
    hospital.save(update_fields=["approval_status", "rejection_reason", "reviewed_at"])


def _notify(hospital: Hospital, outcome: str, detail: str) -> None:
    # v1 uses Django's console email backend; v2 swaps in a real provider.
    send_mail(
        subject=f"SmartCare: your registration was {outcome}",
        message=f"Hello {hospital.name},\n\nYour SmartCare registration was {outcome}. {detail}",
        from_email=None,
        recipient_list=[hospital.email],
    )
