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
