import datetime as dt
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from accounts.models import Role, User
from doctors.models import Doctor, Specialization
from hospitals.models import ApprovalStatus, Hospital
from pharmacy.models import Pharmacy

KNOWN_LOGINS = {
    "admin@smartcare.test": Role.ADMIN,
    "hospital@smartcare.test": Role.HOSPITAL,
    "pending-hospital@smartcare.test": Role.HOSPITAL,
    "doctor@smartcare.test": Role.DOCTOR,
    "pharmacy@smartcare.test": Role.PHARMACY,
    "patient@smartcare.test": Role.PATIENT,
}


def seed(*args) -> str:
    out = StringIO()
    call_command("seed_demo", *args, stdout=out)
    return out.getvalue()


def counts():
    return {
        "users": User.objects.count(),
        "approved": Hospital.objects.approved().count(),
        "pending": Hospital.objects.filter(approval_status=ApprovalStatus.PENDING).count(),
        "rejected": Hospital.objects.filter(approval_status=ApprovalStatus.REJECTED).count(),
        "doctors": Doctor.objects.count(),
        "pharmacies": Pharmacy.objects.count(),
        "patients": User.objects.filter(role=Role.PATIENT).count(),
    }


def test_seed_creates_the_documented_demo_world(db):
    seed()

    c = counts()
    assert (c["approved"], c["pending"], c["rejected"]) == (5, 1, 1)
    assert c["pharmacies"] == 5 and c["patients"] == 10
    for hospital in Hospital.objects.approved():
        assert 3 <= hospital.doctors.count() <= 4
    covered = set(Doctor.objects.values_list("specialization__name", flat=True))
    assert covered == set(Specialization.objects.values_list("name", flat=True))


def test_every_hospital_name_is_marked_demo(db):
    seed()

    assert all("Demo" in name for name in Hospital.objects.values_list("name", flat=True))


def test_all_seeded_emails_use_the_reserved_test_domain(db):
    seed()

    assert not User.objects.exclude(email__endswith="@smartcare.test").exists()


@pytest.mark.parametrize("email,role", KNOWN_LOGINS.items())
def test_known_logins_work(db, client, email, role):
    seed()

    assert client.login(email=email, password="demo-pass-123")
    assert User.objects.get(email=email).role == role


def test_demo_doctor_and_pharmacy_share_a_hospital(db):
    seed()

    doctor = Doctor.objects.get(user__email="doctor@smartcare.test")
    pharmacy = Pharmacy.objects.get(user__email="pharmacy@smartcare.test")
    assert doctor.hospital == pharmacy.hospital
    assert doctor.hospital.user.email == "hospital@smartcare.test"


def test_second_run_changes_nothing_and_explains(db):
    seed()
    before = counts()

    output = seed()

    assert "Demo data already exists. Use --flush to recreate it." in output
    assert counts() == before


def test_flush_recreates_identically(db):
    seed()
    before = counts()
    names = list(Hospital.objects.values_list("name", flat=True))
    doctors = sorted(Doctor.objects.values_list("name", flat=True))

    seed("--flush")

    assert counts() == before
    assert list(Hospital.objects.values_list("name", flat=True)) == names
    assert sorted(Doctor.objects.values_list("name", flat=True)) == doctors


def test_flush_keeps_non_demo_users(db):
    User.objects.create_user("real.admin@example.test", password="x-pass-123")
    seed()

    seed("--flush")

    assert User.objects.filter(email="real.admin@example.test").exists()


def test_flush_removes_staff_added_to_demo_hospitals(db):
    from doctors.services import create_doctor

    seed()
    hospital = Hospital.objects.get(user__email="hospital@smartcare.test")
    create_doctor(
        hospital,
        email="me@example.test",
        password="a-long-pass-123",
        name="Dr Added",
        specialization=Specialization.objects.first(),
        qualification="MBBS",
        experience_years=1,
        gender="female",
    )

    seed("--flush")

    assert not User.objects.filter(email="me@example.test").exists()
    assert not User.objects.filter(role=Role.DOCTOR, doctor__isnull=True).exists()


# ---- Sessions and bookings (milestone 3) -------------------------------------------------------


def _demo_booking():
    from bookings.models import Booking

    return Booking.objects.select_related("session").get(
        patient__email="patient@smartcare.test", session__date=timezone.localdate()
    )


def test_demo_patient_is_waiting_in_the_demo_doctors_queue(db):
    from bookings.queue import queue_status

    seed()

    booking = _demo_booking()
    status = queue_status(booking)
    assert booking.session.doctor.user.email == "doctor@smartcare.test"
    assert booking.session.bookings.count() == 6
    assert (status.token_no, status.current_token, status.state) == (5, 2, "waiting")
    assert status.ahead >= 1


def test_demo_queue_session_has_not_ended_yet_when_possible(db):
    seed()

    session = _demo_booking().session
    last_today = session.doctor.sessions.filter(date=session.date).last()
    assert not session.is_past() or session == last_today


def test_every_doctor_has_sessions_today_and_the_next_two_days(db):
    from bookings.models import ConsultingSession

    seed()

    today = timezone.localdate()
    for doctor in Doctor.objects.all():
        dates = set(doctor.sessions.values_list("date", flat=True))
        assert dates == {today + dt.timedelta(days=n) for n in range(3)}, doctor
    assert not ConsultingSession.objects.filter(
        date=today, start_time__gt=dt.time(8), end_time__lt=dt.time(22)
    ).exists()  # today's two sessions cover 08:00–22:00 between them


def test_todays_bookings_mix_paid_and_pending_with_matching_payments(db):
    from bookings.models import Booking, PaymentStatus
    from payments.models import Payment

    seed()

    today = Booking.objects.filter(session__date=timezone.localdate())
    paid = today.filter(payment_status=PaymentStatus.PAID)
    assert paid.exists()
    assert today.filter(payment_status=PaymentStatus.PENDING).exists()
    assert (
        Payment.objects.count() == Booking.objects.filter(payment_status=PaymentStatus.PAID).count()
    )


def test_flush_recreates_bookings(db):
    from bookings.models import Booking

    seed()
    before = Booking.objects.count()

    seed("--flush")

    assert Booking.objects.count() == before
    assert _demo_booking().token_no == 5
