from django.core.files import File
from django.db import transaction

from accounts.models import Role, User
from core.exceptions import NotAllowed
from doctors.models import Doctor, Specialization
from hospitals.models import Hospital
from hospitals.services import require_approved


@transaction.atomic
def create_doctor(
    hospital: Hospital,
    *,
    email: str,
    password: str,
    name: str,
    specialization: Specialization,
    qualification: str,
    experience_years: int,
    gender: str,
    photo: File | None = None,
) -> Doctor:
    """Create a doctor and their login at an approved hospital (both or neither)."""
    require_approved(hospital)
    user = User.objects.create_user(email, password=password, role=Role.DOCTOR)
    return Doctor.objects.create(
        user=user,
        hospital=hospital,
        name=name,
        specialization=specialization,
        qualification=qualification,
        experience_years=experience_years,
        gender=gender,
        photo=photo or "",
    )


def set_doctor_active(hospital: Hospital, doctor: Doctor, active: bool) -> Doctor:
    """Deactivated doctors can't log in and are hidden from patients; their history is kept."""
    if doctor.hospital_id != hospital.pk:
        raise NotAllowed("This doctor belongs to another hospital.")
    doctor.user.is_active = active
    doctor.user.save(update_fields=["is_active"])
    return doctor
