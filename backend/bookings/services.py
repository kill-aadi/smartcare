import datetime as dt
from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from accounts.models import User
from bookings.models import Booking, BookingStatus, ConsultingSession
from core.exceptions import DomainError, NotAllowed
from doctors.models import Doctor


class SessionInPast(DomainError):
    code = "session_in_past"


class SessionOverlap(DomainError):
    code = "session_overlap"


class SessionNotFound(DomainError):
    code = "session_not_found"
    status = 404


class AlreadyBooked(DomainError):
    code = "already_booked"
    status = 409


class SessionFull(DomainError):
    code = "session_full"
    status = 409


@transaction.atomic
def create_session(
    doctor: Doctor,
    *,
    date: dt.date,
    start_time: dt.time,
    end_time: dt.time,
    fee: Decimal,
    capacity: int,
    avg_consult_minutes: int = 10,
    now: dt.datetime | None = None,
) -> ConsultingSession:
    """Add a consulting session. It must end in the future and not overlap the doctor's others."""
    session = ConsultingSession(
        doctor=doctor,
        date=date,
        start_time=start_time,
        end_time=end_time,
        fee=fee,
        capacity=capacity,
        avg_consult_minutes=avg_consult_minutes,
    )
    if session.is_past(now or timezone.now()):
        raise SessionInPast("This session would already be over. Pick a later date or time.")
    # Lock the doctor row so two tabs can't both pass the overlap check at once.
    Doctor.objects.select_for_update().filter(pk=doctor.pk).first()
    overlapping = doctor.sessions.filter(
        date=date, start_time__lt=end_time, end_time__gt=start_time
    )
    if overlapping.exists():
        raise SessionOverlap("This overlaps another of your sessions on that day.")
    session.save()
    return session


def _active(bookings):
    return bookings.exclude(status=BookingStatus.CANCELLED)


def seats_left(session: ConsultingSession) -> int:
    return max(session.capacity - _active(session.bookings).count(), 0)


@transaction.atomic
def book_session(
    patient: User, session_id: int, description: str = "", *, now: dt.datetime | None = None
) -> Booking:
    """Book a seat and hand out the next token number.

    The session row is locked (``SELECT ... FOR UPDATE``) for the rest of the transaction, so
    concurrent bookings for the same session run one at a time: each sees the previous one's
    token and seat count. Tokens are never reused, even after a cancellation.
    """
    try:
        session = ConsultingSession.objects.select_for_update().get(
            pk=session_id, doctor__in=Doctor.objects.visible_to_patients()
        )
    except ConsultingSession.DoesNotExist:
        raise SessionNotFound("This session isn't available.") from None
    if session.is_past(now or timezone.now()):
        raise SessionInPast("This session has already ended.")
    if _active(session.bookings).filter(patient=patient).exists():
        raise AlreadyBooked("You already have a booking for this session.")
    if seats_left(session) == 0:
        raise SessionFull("This session is full. Try another session.")
    last_token = session.bookings.aggregate(last=Max("token_no"))["last"] or 0
    return Booking.objects.create(
        session=session, patient=patient, description=description, token_no=last_token + 1
    )


@transaction.atomic
def cancel_booking(patient: User, booking: Booking, *, now: dt.datetime | None = None) -> Booking:
    """Cancel the patient's own booking before the session ends. The seat is freed."""
    booking = Booking.objects.select_for_update().select_related("session").get(pk=booking.pk)
    if booking.patient_id != patient.pk:
        raise NotAllowed("This isn't your booking.")
    if booking.status != BookingStatus.BOOKED:
        raise NotAllowed("Only an active booking can be cancelled.")
    if booking.session.is_past(now or timezone.now()):
        raise NotAllowed("This session has already ended.")
    booking.status = BookingStatus.CANCELLED
    booking.save(update_fields=["status"])
    return booking
