"""factory_boy factories shared by every app's tests. All data is fictional."""

import datetime as dt
from decimal import Decimal

import factory
from django.core.files.base import ContentFile
from django.utils import timezone

from accounts.models import Gender, PatientProfile, Role, User
from bookings.models import ConsultingSession
from doctors.models import Doctor, Specialization
from hospitals.models import ApprovalStatus, Hospital
from pharmacy.models import Pharmacy

TEST_PASSWORD = "x-pass-123"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.test")
    role = Role.PATIENT
    password = factory.PostGenerationMethodCall("set_password", TEST_PASSWORD)

    @factory.post_generation
    def _save(obj, create, extracted, **kwargs):  # persist the hashed password
        if create:
            obj.save()


class HospitalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Hospital

    user = factory.SubFactory(UserFactory, role=Role.HOSPITAL)
    name = factory.Sequence(lambda n: f"Test Hospital {n}")
    place = "Thrissur"
    phone = "0487 000 0000"
    email = factory.LazyAttribute(lambda o: o.user.email)
    licence_proof = factory.LazyFunction(lambda: ContentFile(b"%PDF-1.4 test", name="licence.pdf"))
    latitude = Decimal("10.527642")
    longitude = Decimal("76.214435")
    approval_status = ApprovalStatus.APPROVED


class SpecializationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Specialization
        django_get_or_create = ["name"]

    name = "General Physician"
    description = "Fictional test description."


class DoctorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Doctor

    user = factory.SubFactory(UserFactory, role=Role.DOCTOR)
    hospital = factory.SubFactory(HospitalFactory)
    name = factory.Sequence(lambda n: f"Dr Test {n}")
    specialization = factory.SubFactory(SpecializationFactory)
    qualification = "MBBS"
    experience_years = 5
    gender = Gender.FEMALE


class PharmacyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Pharmacy

    user = factory.SubFactory(UserFactory, role=Role.PHARMACY)
    hospital = factory.SubFactory(HospitalFactory)
    name = factory.Sequence(lambda n: f"Test Pharmacy {n}")
    phone = "0487 111 1111"
    email = factory.LazyAttribute(lambda o: o.user.email)


class SessionFactory(factory.django.DjangoModelFactory):
    """A bookable session tomorrow (IST) with a visible doctor."""

    class Meta:
        model = ConsultingSession

    doctor = factory.SubFactory(DoctorFactory)
    date = factory.LazyFunction(lambda: timezone.localdate() + dt.timedelta(days=1))
    start_time = dt.time(9, 0)
    end_time = dt.time(12, 0)
    fee = Decimal("300.00")
    capacity = 20


class PatientProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PatientProfile

    user = factory.SubFactory(UserFactory, role=Role.PATIENT)
    name = factory.Sequence(lambda n: f"Patient {n}")
    phone = "90000 00000"
    gender = Gender.OTHER
    place = "Thrissur"


def PatientFactory(**kwargs) -> User:  # noqa: N802 - reads like the other factories at call sites
    """Create a patient ``User`` with a profile and return the user."""
    return PatientProfileFactory(**kwargs).user


def _patient_batch(size: int, **kwargs) -> list[User]:
    return [PatientFactory(**kwargs) for _ in range(size)]


PatientFactory.create_batch = _patient_batch
