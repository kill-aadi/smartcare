import datetime as dt

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
