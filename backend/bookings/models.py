import datetime as dt

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from doctors.models import Doctor


class ConsultingSession(models.Model):
    """A block of time when a doctor sees patients (the report's "Consulting Time")."""

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="sessions")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    fee = models.DecimalField(max_digits=8, decimal_places=2)
    capacity = models.PositiveSmallIntegerField()
    current_token = models.PositiveSmallIntegerField(default=0)
    avg_consult_minutes = models.PositiveSmallIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "start_time"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")), name="session_ends_after_start"
            ),
            models.CheckConstraint(condition=Q(capacity__gte=1), name="session_capacity_min_1"),
            models.CheckConstraint(condition=Q(fee__gte=0), name="session_fee_not_negative"),
        ]

    def __str__(self) -> str:
        return f"{self.doctor} · {self.date} {self.start_time:%H:%M}–{self.end_time:%H:%M}"

    def starts_at(self) -> dt.datetime:
        return dt.datetime.combine(
            self.date, self.start_time, tzinfo=timezone.get_default_timezone()
        )

    def ends_at(self) -> dt.datetime:
        return dt.datetime.combine(self.date, self.end_time, tzinfo=timezone.get_default_timezone())

    def is_past(self, now: dt.datetime | None = None) -> bool:
        return self.ends_at() <= (now or timezone.now())


class BookingStatus(models.TextChoices):
    BOOKED = "booked", "Booked"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"
    NO_SHOW = "no_show", "No-show"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"


class Booking(models.Model):
    """A patient's place in a session. ``token_no`` is their number in the queue."""

    session = models.ForeignKey(
        ConsultingSession, on_delete=models.CASCADE, related_name="bookings"
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings"
    )
    description = models.CharField(max_length=500, blank=True)
    token_no = models.PositiveSmallIntegerField()
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    status = models.CharField(
        max_length=10, choices=BookingStatus.choices, default=BookingStatus.BOOKED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["session", "token_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "token_no"], name="unique_token_per_session"
            ),
            models.UniqueConstraint(
                fields=["session", "patient"],
                condition=~Q(status="cancelled"),
                name="one_active_booking_per_patient_session",
            ),
        ]

    def __str__(self) -> str:
        return f"Token {self.token_no} · {self.session}"
