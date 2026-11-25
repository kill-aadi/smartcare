"""Create a fictional, deterministic demo world: `python manage.py seed_demo [--flush]`.

Every account uses an @smartcare.test email (a reserved test domain) and the password below.
Hospital names all contain "Demo" so nobody mistakes them for real hospitals.
"""

import datetime as dt
import random
from dataclasses import dataclass
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from faker import Faker

from accounts.models import Gender, PatientProfile, Role, User
from bookings.models import Booking, BookingStatus, ConsultingSession
from doctors.models import Doctor, Specialization
from doctors.services import create_doctor
from hospitals.models import ApprovalStatus, Hospital
from hospitals.services import register_hospital
from payments.services import pay_booking
from pharmacy.services import create_pharmacy

DEMO_DOMAIN = "@smartcare.test"
DEMO_PASSWORD = "demo-pass-123"
SEED = 42


@dataclass(frozen=True)
class DemoHospital:
    name: str
    place: str
    lat: str
    lng: str
    status: str = ApprovalStatus.APPROVED
    login: str | None = None  # a documented login; others get generated emails


HOSPITALS = [
    DemoHospital(
        "Riverside Demo Hospital",
        "Thrissur",
        "10.527642",
        "76.214435",
        login="hospital@smartcare.test",
    ),
    DemoHospital("Lakeview Demo Medical Centre", "Irinjalakuda", "10.342400", "76.211200"),
    DemoHospital("Greenfield Demo Hospital", "Chalakudy", "10.307000", "76.334100"),
    DemoHospital("Temple Town Demo Clinic", "Guruvayur", "10.594600", "76.036900"),
    DemoHospital("Seaside Demo Hospital", "Kodungallur", "10.224300", "76.198300"),
    DemoHospital(
        "Hilltop Demo Hospital",
        "Ollur",
        "10.477000",
        "76.247000",
        status=ApprovalStatus.PENDING,
        login="pending-hospital@smartcare.test",
    ),
    DemoHospital(
        "Old Mill Demo Clinic",
        "Kunnamkulam",
        "10.650000",
        "76.070000",
        status=ApprovalStatus.REJECTED,
        login="rejected-hospital@smartcare.test",
    ),
]

# Doctors per approved hospital, in order. Every hospital has a General Physician; together the
# five hospitals cover all twelve specialisations.
DOCTOR_PLAN = [
    ["General Physician", "Dermatology", "Cardiology", "ENT"],
    ["General Physician", "Pulmonology", "Neurology", "Gynaecology"],
    ["General Physician", "Orthopaedics", "Gastroenterology"],
    ["General Physician", "Urology", "Endocrinology"],
    ["General Physician", "General Surgery", "Dermatology"],
]
QUALIFICATIONS = {"General Physician": "MBBS", "General Surgery": "MBBS, MS"}

COMPLAINTS = [
    "",
    "Fever and body ache for three days",
    "Follow-up visit",
    "Dry cough at night",
    "Skin rash on the arms",
    "Headache since last week",
    "Knee pain when climbing stairs",
]

# Today is split into two sessions so a demo queue is open at any hour from 08:00 to 22:00 IST.
TODAY_SLOTS = [(dt.time(8), dt.time(15)), (dt.time(15), dt.time(22))]
LATER_SLOTS = [(dt.time(9), dt.time(13)), (dt.time(14), dt.time(18))]
FEES = [Decimal("200"), Decimal("300"), Decimal("400"), Decimal("500")]
DEMO_QUEUE_SIZE = 6  # doctor@'s live session: tokens 1-6, now serving 2, patient@ holds 5
DEMO_PATIENT_TOKEN = 5


class Command(BaseCommand):
    help = "Create fictional demo data (hospitals, doctors, pharmacies, patients, bookings)."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Delete demo data and reseed.")

    @transaction.atomic
    def handle(self, *args, flush=False, **options):
        if flush:
            # Demo accounts, plus any staff someone added to a demo hospital while trying it out
            # (otherwise their logins would survive without a doctor/pharmacy profile).
            demo_users = User.objects.filter(
                Q(email__endswith=DEMO_DOMAIN)
                | Q(doctor__hospital__user__email__endswith=DEMO_DOMAIN)
                | Q(pharmacy__hospital__user__email__endswith=DEMO_DOMAIN)
            )
            deleted, _ = demo_users.delete()
            self.stdout.write(f"Removed existing demo data ({deleted} rows).")
        elif User.objects.filter(email=f"admin{DEMO_DOMAIN}").exists():
            self.stdout.write("Demo data already exists. Use --flush to recreate it.")
            return

        random.seed(SEED)
        self.fake = Faker("en_IN")
        self.fake.seed_instance(SEED)

        self._seed_people()
        self._seed_sessions_and_bookings()
        self.stdout.write(self.style.SUCCESS("Demo data created. Logins use " + DEMO_PASSWORD))

    # ---- steps (later milestones add _seed_sessions(), _seed_prescriptions(), ...) -------------

    def _seed_people(self) -> None:
        User.objects.create_superuser(f"admin{DEMO_DOMAIN}", password=DEMO_PASSWORD)
        admin = User.objects.get(email=f"admin{DEMO_DOMAIN}")

        approved = []
        for i, spec in enumerate(HOSPITALS, start=1):
            hospital = register_hospital(
                email=spec.login or f"hospital{i}{DEMO_DOMAIN}",
                password=DEMO_PASSWORD,
                name=spec.name,
                place=spec.place,
                phone=f"0487 {200000 + i:06d}",
                latitude=Decimal(spec.lat),
                longitude=Decimal(spec.lng),
                licence_proof=ContentFile(b"%PDF-1.4\n% fictional demo licence\n", "licence.pdf"),
            )
            self._set_status(hospital, spec.status, admin)
            if spec.status == ApprovalStatus.APPROVED:
                approved.append(hospital)

        specializations = {s.name: s for s in Specialization.objects.all()}
        for h_index, (hospital, plan) in enumerate(zip(approved, DOCTOR_PLAN, strict=True)):
            for d_index, spec_name in enumerate(plan):
                is_demo_doctor = h_index == 0 and d_index == 0
                create_doctor(
                    hospital,
                    email="doctor@smartcare.test"
                    if is_demo_doctor
                    else f"doctor{h_index + 1}-{d_index + 1}{DEMO_DOMAIN}",
                    password=DEMO_PASSWORD,
                    name=f"Dr {self.fake.first_name()} {self.fake.last_name()}",
                    specialization=specializations[spec_name],
                    qualification=QUALIFICATIONS.get(spec_name, "MBBS, MD"),
                    experience_years=random.randint(3, 25),
                    gender=random.choice([Gender.FEMALE, Gender.MALE]),
                )
            create_pharmacy(
                hospital,
                email="pharmacy@smartcare.test"
                if h_index == 0
                else f"pharmacy{h_index + 1}{DEMO_DOMAIN}",
                password=DEMO_PASSWORD,
                name=f"{hospital.name.split(' Demo')[0]} Demo Pharmacy",
                phone=f"0487 {300000 + h_index:06d}",
            )

        places = [h.place for h in HOSPITALS[:5]]
        for i in range(10):
            user = User.objects.create_user(
                "patient@smartcare.test" if i == 0 else f"patient{i + 1}{DEMO_DOMAIN}",
                password=DEMO_PASSWORD,
                role=Role.PATIENT,
            )
            PatientProfile.objects.create(
                user=user,
                name=self.fake.name(),
                phone=f"9{random.randint(100000000, 999999999)}",
                date_of_birth=self.fake.date_of_birth(minimum_age=18, maximum_age=80),
                gender=random.choice(list(Gender.values)),
                place=random.choice(places),
            )

        self.stdout.write(
            f"  {len(approved)} approved hospitals, {Doctor.objects.count()} doctors, "
            f"{len(approved)} pharmacies, 10 patients"
        )

    def _seed_sessions_and_bookings(self) -> None:
        today = timezone.localdate()
        demo_patient = User.objects.get(email="patient@smartcare.test")
        others = list(User.objects.filter(role=Role.PATIENT).exclude(pk=demo_patient.pk))

        for i, doctor in enumerate(Doctor.objects.order_by("pk")):
            fee = random.choice(FEES)
            todays = [self._session(doctor, today, start, end, fee) for start, end in TODAY_SLOTS]
            for days in (1, 2):
                start, end = LATER_SLOTS[(i + days) % 2]
                self._session(doctor, today + dt.timedelta(days=days), start, end, fee)

            if doctor.user.email == "doctor@smartcare.test":
                self._seed_demo_queue(self.live_session(todays), demo_patient, others)
            else:
                for session in todays:
                    patients = random.sample(others, random.randint(0, 4))
                    self._book(session, patients, paid=[random.random() < 0.6 for _ in patients])

        self.stdout.write(
            f"  {ConsultingSession.objects.count()} sessions, {Booking.objects.count()} bookings; "
            f"patient@ holds token {DEMO_PATIENT_TOKEN} in doctor@'s queue"
        )

    @staticmethod
    def live_session(sessions: list[ConsultingSession]) -> ConsultingSession:
        """Today's first session that hasn't ended, else the last one (seeded after 22:00)."""
        return next((s for s in sessions if not s.is_past()), sessions[-1])

    def _seed_demo_queue(self, session, demo_patient, others) -> None:
        patients = random.sample(others, DEMO_QUEUE_SIZE - 1)
        patients.insert(DEMO_PATIENT_TOKEN - 1, demo_patient)
        bookings = self._book(session, patients, paid=[True, True, False, True, True, False])
        bookings[0].status = BookingStatus.COMPLETED  # token 1 seen, token 2 with the doctor now
        bookings[0].save(update_fields=["status"])
        session.current_token = 2
        session.save(update_fields=["current_token"])

    @staticmethod
    def _session(doctor, date, start, end, fee) -> ConsultingSession:
        # Created directly: create_session() refuses sessions already over (a seed run at 16:00
        # must still create the 08:00-15:00 one).
        return ConsultingSession.objects.create(
            doctor=doctor, date=date, start_time=start, end_time=end, fee=fee, capacity=20
        )

    def _book(self, session, patients, paid) -> list[Booking]:
        # Direct create for the same reason; tokens are sequential exactly as book_session() would.
        bookings = []
        for token, (patient, is_paid) in enumerate(zip(patients, paid, strict=True), start=1):
            booking = Booking.objects.create(
                session=session,
                patient=patient,
                token_no=token,
                description=random.choice(COMPLAINTS),
            )
            if is_paid:
                pay_booking(patient, booking)
            bookings.append(booking)
        return bookings

    @staticmethod
    def _set_status(hospital: Hospital, status: str, admin: User) -> None:
        if status == ApprovalStatus.PENDING:
            return
        hospital.approval_status = status
        hospital.reviewed_at = timezone.now()
        if status == ApprovalStatus.REJECTED:
            hospital.rejection_reason = "The licence document could not be read. (Demo data.)"
        hospital.save()
