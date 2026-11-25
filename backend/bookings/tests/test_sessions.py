import datetime as dt
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from bookings.models import ConsultingSession
from bookings.services import SessionInPast, SessionOverlap, create_session
from core.factories import DoctorFactory, SessionFactory

IST = timezone.get_default_timezone()
# 10:00 IST on a fixed day, so "past" and "today" never depend on when the suite runs.
NOW = dt.datetime(2030, 1, 15, 10, 0, tzinfo=IST)
TODAY = NOW.date()
TOMORROW = TODAY + dt.timedelta(days=1)


def _create(doctor, start, end, date=TOMORROW, **kw):
    return create_session(
        doctor,
        date=date,
        start_time=dt.time(*start),
        end_time=dt.time(*end),
        fee=kw.pop("fee", Decimal("300.00")),
        capacity=kw.pop("capacity", 20),
        now=NOW,
        **kw,
    )


def test_create_session(db):
    doctor = DoctorFactory()

    session = _create(doctor, (9, 0), (12, 0), avg_consult_minutes=15)

    assert session.doctor == doctor
    assert session.current_token == 0
    assert session.avg_consult_minutes == 15
    assert session.starts_at() == dt.datetime(2030, 1, 16, 9, 0, tzinfo=IST)
    assert session.ends_at() == dt.datetime(2030, 1, 16, 12, 0, tzinfo=IST)


def test_default_avg_consult_minutes_is_10(db):
    assert _create(DoctorFactory(), (9, 0), (12, 0)).avg_consult_minutes == 10


@pytest.mark.parametrize(
    ("date", "start", "end"),
    [
        (TODAY - dt.timedelta(days=1), (9, 0), (12, 0)),  # yesterday
        (TODAY, (8, 0), (10, 0)),  # ends exactly now
    ],
)
def test_session_in_the_past_is_rejected(db, date, start, end):
    with pytest.raises(SessionInPast):
        _create(DoctorFactory(), start, end, date=date)

    assert not ConsultingSession.objects.exists()


def test_session_already_running_today_is_allowed(db):
    session = _create(DoctorFactory(), (9, 0), (11, 0), date=TODAY)

    assert not session.is_past(NOW)


def test_overlapping_session_is_rejected(db):
    doctor = DoctorFactory()
    _create(doctor, (10, 0), (12, 0))

    with pytest.raises(SessionOverlap):
        _create(doctor, (9, 0), (11, 0))

    assert doctor.sessions.count() == 1


def test_back_to_back_sessions_are_allowed(db):
    doctor = DoctorFactory()
    _create(doctor, (9, 0), (11, 0))

    _create(doctor, (11, 0), (12, 0))

    assert doctor.sessions.count() == 2


def test_another_doctor_may_use_the_same_hours(db):
    _create(DoctorFactory(), (9, 0), (11, 0))

    _create(DoctorFactory(), (9, 0), (11, 0))

    assert ConsultingSession.objects.count() == 2


def test_same_hours_on_another_day_are_allowed(db):
    doctor = DoctorFactory()
    _create(doctor, (9, 0), (11, 0))

    _create(doctor, (9, 0), (11, 0), date=TOMORROW + dt.timedelta(days=1))

    assert doctor.sessions.count() == 2


@pytest.mark.parametrize(
    "fields",
    [
        {"start_time": dt.time(12, 0), "end_time": dt.time(9, 0)},
        {"capacity": 0},
        {"fee": Decimal("-1")},
    ],
)
def test_database_rejects_invalid_sessions(db, fields):
    with pytest.raises(IntegrityError), transaction.atomic():
        SessionFactory(**fields)


# ---- Doctor dashboard ----------------------------------------------------------------------------

SESSIONS_URL = "/dashboard/doctor/sessions/"


def _form(**overrides):
    tomorrow = timezone.localdate() + dt.timedelta(days=1)
    return {
        "date": tomorrow.isoformat(),
        "start_time": "09:00",
        "end_time": "12:00",
        "fee": "300",
        "capacity": "20",
        "avg_consult_minutes": "10",
    } | overrides


@pytest.fixture
def doctor_client(client, db):
    doctor = DoctorFactory()
    client.force_login(doctor.user)
    client.doctor = doctor
    return client


def test_doctor_creates_a_session_from_the_dashboard(doctor_client):
    response = doctor_client.post(SESSIONS_URL, _form(), follow=True)

    assert response.redirect_chain[-1][0] == SESSIONS_URL
    session = doctor_client.doctor.sessions.get()
    assert session.capacity == 20
    assert b"Session added" in response.content


def test_end_before_start_is_a_form_error(doctor_client):
    response = doctor_client.post(SESSIONS_URL, _form(start_time="12:00", end_time="09:00"))

    assert response.status_code == 200
    assert "end_time" in response.context["form"].errors
    assert not ConsultingSession.objects.exists()


def test_capacity_zero_is_a_form_error(doctor_client):
    response = doctor_client.post(SESSIONS_URL, _form(capacity="0"))

    assert "capacity" in response.context["form"].errors


def test_service_errors_show_on_the_form(doctor_client):
    yesterday = timezone.localdate() - dt.timedelta(days=1)

    response = doctor_client.post(SESSIONS_URL, _form(date=yesterday.isoformat()))

    assert response.status_code == 200
    assert response.context["form"].non_field_errors()
    assert not ConsultingSession.objects.exists()


def test_doctor_sees_only_own_upcoming_sessions(doctor_client):
    tomorrow = timezone.localdate() + dt.timedelta(days=1)
    SessionFactory(doctor=doctor_client.doctor, date=tomorrow, fee=Decimal("111"))
    SessionFactory(
        doctor=doctor_client.doctor, date=tomorrow - dt.timedelta(days=3), fee=Decimal("222")
    )
    SessionFactory(date=tomorrow, fee=Decimal("333"))  # another doctor's

    response = doctor_client.get(SESSIONS_URL)

    assert list(response.context["sessions"]) == [doctor_client.doctor.sessions.get(fee=111)]
    assert b"333" not in response.content


@pytest.mark.parametrize("role_factory", ["hospital", "patient"])
def test_sessions_page_is_doctor_only(client, db, role_factory):
    from core.factories import HospitalFactory, PatientFactory

    user = HospitalFactory().user if role_factory == "hospital" else PatientFactory()
    client.force_login(user)

    assert client.get(SESSIONS_URL).status_code == 403
