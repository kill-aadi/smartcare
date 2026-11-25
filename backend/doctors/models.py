from django.conf import settings
from django.db import models

from accounts.models import Gender
from hospitals.models import ApprovalStatus


class Specialization(models.Model):
    """A kind of doctor (e.g. Dermatology). The AI suggestion maps symptoms to one of these."""

    name = models.CharField(max_length=60, unique=True)
    description = models.TextField()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class DoctorQuerySet(models.QuerySet):
    def visible_to_patients(self):
        """Patients only ever see active doctors at approved hospitals."""
        return self.filter(user__is_active=True, hospital__approval_status=ApprovalStatus.APPROVED)


class Doctor(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="doctor"
    )
    hospital = models.ForeignKey(
        "hospitals.Hospital", on_delete=models.CASCADE, related_name="doctors"
    )
    name = models.CharField(max_length=120)
    specialization = models.ForeignKey(
        Specialization, on_delete=models.PROTECT, related_name="doctors"
    )
    qualification = models.CharField(max_length=120)
    experience_years = models.PositiveSmallIntegerField()
    gender = models.CharField(max_length=10, choices=Gender.choices)
    photo = models.ImageField(upload_to="doctors/photos/", blank=True)

    objects = DoctorQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.specialization})"
