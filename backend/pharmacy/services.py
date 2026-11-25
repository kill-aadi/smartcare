from django.db import transaction

from accounts.models import Role, User
from hospitals.models import Hospital
from hospitals.services import require_approved
from pharmacy.models import Pharmacy


@transaction.atomic
def create_pharmacy(
    hospital: Hospital, *, email: str, password: str, name: str, phone: str
) -> Pharmacy:
    """Create a pharmacy and its login at an approved hospital (both or neither)."""
    require_approved(hospital)
    user = User.objects.create_user(email, password=password, role=Role.PHARMACY)
    return Pharmacy.objects.create(
        user=user, hospital=hospital, name=name, phone=phone, email=user.email
    )
