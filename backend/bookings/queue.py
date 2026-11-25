"""The live queue: the doctor calls the next token, the patient app reads queue_status()."""

import datetime as dt
from dataclasses import dataclass
from typing import Literal

from django.db import transaction
from django.utils import timezone

from bookings.models import Booking, BookingStatus, ConsultingSession
from core.exceptions import DomainError, InvalidTransition, NotAllowed
from doctors.models import Doctor


class NotToday(DomainError):
    code = "not_today"


class CurrentNotClosed(DomainError):
    code = "current_not_closed"


@dataclass(frozen=True)
class QueueStatus:
    token_no: int
    current_token: int
    ahead: int
    eta_minutes: int
    state: Literal["waiting", "now_serving", "done", "cancelled"]


def _require_own(doctor: Doctor, session: ConsultingSession) -> None:
    if session.doctor_id != doctor.pk:
        raise NotAllowed("This is another doctor's session.")


@transaction.atomic
def call_next(
    doctor: Doctor, session: ConsultingSession, *, today: dt.date | None = None
) -> int | None:
    """Move ``current_token`` to the next active booking. Returns it, or None if nobody's left."""
    session = ConsultingSession.objects.select_for_update().get(pk=session.pk)
    _require_own(doctor, session)
    if session.date != (today or timezone.localdate()):
        raise NotToday("You can only call patients on the day of the session.")
    if session.bookings.filter(
        token_no=session.current_token, status=BookingStatus.BOOKED
    ).exists():
        raise CurrentNotClosed(
            f"Mark token {session.current_token} complete or no-show before calling the next one."
        )
    next_booking = (
        session.bookings.filter(status=BookingStatus.BOOKED, token_no__gt=session.current_token)
        .order_by("token_no")
        .first()
    )
    if next_booking is None:
        return None
    session.current_token = next_booking.token_no
    session.save(update_fields=["current_token"])
    return session.current_token


@transaction.atomic
def _close(doctor: Doctor, booking: Booking, status: str) -> Booking:
    booking = Booking.objects.select_for_update().select_related("session").get(pk=booking.pk)
    _require_own(doctor, booking.session)
    if booking.status != BookingStatus.BOOKED:
        raise InvalidTransition("This booking is already closed.")
    if booking.token_no > booking.session.current_token:
        raise InvalidTransition("This token hasn't been called yet.")
    booking.status = status
    booking.save(update_fields=["status"])
    return booking


def complete_booking(doctor: Doctor, booking: Booking) -> Booking:
    """Mark the consultation complete without a prescription."""
    return _close(doctor, booking, BookingStatus.COMPLETED)


def mark_no_show(doctor: Doctor, booking: Booking) -> Booking:
    return _close(doctor, booking, BookingStatus.NO_SHOW)


def queue_status(booking: Booking, *, now: dt.datetime | None = None) -> QueueStatus:
    """Where a booking stands in its session's queue. ETA is an estimate, never a promise.

    A booking still waiting when its session has ended is "done": it will never be called.
    """
    session = booking.session
    current = session.current_token
    if booking.status == BookingStatus.CANCELLED:
        state = "cancelled"
    elif booking.status != BookingStatus.BOOKED or booking.token_no < current:
        state = "done"
    elif booking.token_no == current:
        state = "now_serving"
    elif session.is_past(now):
        state = "done"
    else:
        state = "waiting"
    if state == "waiting":
        ahead = session.bookings.filter(
            status=BookingStatus.BOOKED, token_no__gt=current, token_no__lt=booking.token_no
        ).count()
        eta = (booking.token_no - current) * session.avg_consult_minutes
    else:
        ahead, eta = 0, 0
    return QueueStatus(
        token_no=booking.token_no, current_token=current, ahead=ahead, eta_minutes=eta, state=state
    )
