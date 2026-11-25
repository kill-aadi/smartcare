from datetime import date

from django.db import transaction

from accounts.models import PatientProfile, Role, User


@transaction.atomic
def register_patient(
    *,
    email: str,
    password: str,
    name: str,
    phone: str,
    gender: str,
    date_of_birth: date | None = None,
    place: str = "",
) -> User:
    """Create a patient login and profile together (both or neither)."""
    user = User.objects.create_user(email, password=password, role=Role.PATIENT)
    PatientProfile.objects.create(
        user=user, name=name, phone=phone, gender=gender, date_of_birth=date_of_birth, place=place
    )
    return user
