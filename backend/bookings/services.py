import datetime as dt
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from bookings.models import ConsultingSession
from core.exceptions import DomainError
from doctors.models import Doctor


class SessionInPast(DomainError):
    code = "session_in_past"


class SessionOverlap(DomainError):
    code = "session_overlap"


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
