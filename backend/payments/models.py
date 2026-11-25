import uuid

from django.conf import settings
from django.db import models


def new_reference() -> str:
    return "SIM-" + uuid.uuid4().hex[:12].upper()


class Payment(models.Model):
    """A record of money paid. v1 only simulates payment (see ADR 0008)."""

    booking = models.ForeignKey(
        "bookings.Booking", null=True, blank=True, on_delete=models.CASCADE, related_name="payments"
    )
    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    provider = models.CharField(max_length=20, default="simulated")
    reference = models.CharField(max_length=40, unique=True, default=new_reference)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.reference} · ₹{self.amount}"
