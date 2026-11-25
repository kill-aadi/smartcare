from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from accounts.managers import UserManager


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    HOSPITAL = "hospital", "Hospital"
    DOCTOR = "doctor", "Doctor"
    PHARMACY = "pharmacy", "Pharmacy"
    PATIENT = "patient", "Patient"


class Gender(models.TextChoices):
    FEMALE = "female", "Female"
    MALE = "male", "Male"
    OTHER = "other", "Other"


DUPLICATE_EMAIL_MESSAGE = "A user with that email already exists."


class User(AbstractUser):
    """One account type for all five roles; ``role`` decides which dashboard or app a user gets."""

    username = None
    first_name = None
    last_name = None
    email = models.EmailField(
        "email address",
        unique=True,
        error_messages={"unique": DUPLICATE_EMAIL_MESSAGE},
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.PATIENT)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="user_email_ci_unique",
                violation_error_message=DUPLICATE_EMAIL_MESSAGE,
            ),
        ]

    def clean(self):
        # Forms (dashboards, Django admin) call clean(); the manager handles create_user().
        super().clean()
        self.email = (self.email or "").strip().lower()

    def __str__(self):
        return f"{self.email} ({self.role})"


class PatientProfile(models.Model):
    """Extra details for a patient; staff roles keep theirs on Hospital, Doctor or Pharmacy."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="patient_profile")
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    place = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name
