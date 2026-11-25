from django.conf import settings
from django.db import models


class ApprovalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class HospitalQuerySet(models.QuerySet):
    def approved(self):
        return self.filter(approval_status=ApprovalStatus.APPROVED)


class Hospital(models.Model):
    """A hospital account. It self-registers as pending; an admin approves or rejects it."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hospital"
    )
    name = models.CharField(max_length=150)
    place = models.CharField(max_length=100)
    phone = models.CharField(max_length=30)
    email = models.EmailField()
    photo = models.ImageField(upload_to="hospitals/photos/", blank=True)
    # Private: served only through the admin-only licence view, never from MEDIA_URL.
    licence_proof = models.FileField(upload_to="licences/")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    approval_status = models.CharField(
        max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING
    )
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    objects = HospitalQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
