import datetime as dt
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from bookings.models import Booking, BookingStatus
from bookings.services import book_session, cancel_booking
from core.factories import (
    BookingFactory,
    DoctorFactory,
    HospitalFactory,
    PatientFactory,
    SessionFactory,
)
from hospitals.models import ApprovalStatus

TODAY = timezone.localdate()


def _api(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def patient(db):
    return PatientFactory()


@pytest.fixture
def api(patient):
    return _api(patient)


@pytest.fixture
def session(db):
    return SessionFactory(fee=Decimal("400.00"), capacity=3)


def _book(api, session, **extra):
    return api.post("/api/bookings/", {"session": session.pk, **extra}, format="json")


def test_book_pay_and_follow_the_queue(api, session):
    sessions = api.get(f"/api/doctors/{session.doctor.pk}/sessions/")
    assert sessions.status_code == 200
    assert sessions.data[0]["id"] == session.pk
    assert sessions.data[0]["seats_left"] == 3

    booked = _book(api, session, description="Cough for a week")
    assert booked.status_code == 201
    booking_id = booked.data["id"]
    assert booked.data["token_no"] == 1
    assert booked.data["status"] == "booked"
    assert booked.data["payment_status"] == "pending"
    assert booked.data["doctor"]["name"] == session.doctor.name
    assert booked.data["hospital"]["id"] == session.doctor.hospital.pk
    assert booked.data["has_prescription"] is False

    paid = api.post(f"/api/bookings/{booking_id}/pay/")
    assert paid.status_code == 200
    assert paid.data["provider"] == "simulated"
    assert Decimal(paid.data["amount"]) == Decimal("400.00")
    assert paid.data["reference"].startswith("SIM-")

    queue = api.get(f"/api/bookings/{booking_id}/queue/")
    assert queue.status_code == 200
    assert queue.data == {
        "token_no": 1,
        "current_token": 0,
        "ahead": 0,
        "eta_minutes": 10,
        "state": "waiting",
    }

    detail = api.get(f"/api/bookings/{booking_id}/")
    assert detail.data["payment_status"] == "paid"


def test_booking_json_shape(api, session):
    data = _book(api, session).data

    assert set(data) == {
        "id",
        "token_no",
        "status",
        "payment_status",
        "description",
        "created_at",
        "session",
        "doctor",
        "hospital",
        "has_prescription",
    }
    assert set(data["session"]) == {"id", "date", "start_time", "end_time", "fee"}
    assert set(data["doctor"]) == {"id", "name", "specialization"}
    assert set(data["hospital"]) == {"id", "name", "latitude", "longitude"}


@pytest.mark.parametrize(
    ("method", "suffix"),
    [("get", ""), ("get", "queue/"), ("post", "pay/"), ("post", "cancel/")],
)
def test_another_patients_booking_is_404(api, session, method, suffix):
    theirs = book_session(PatientFactory(), session.pk)

    response = getattr(api, method)(f"/api/bookings/{theirs.pk}/{suffix}")

    assert response.status_code == 404
    theirs.refresh_from_db()
    assert (theirs.status, theirs.payment_status) == ("booked", "pending")


def test_double_tap_book_is_409_with_one_booking(api, session):
    _book(api, session)

    second = _book(api, session)

    assert second.status_code == 409
    assert second.data["code"] == "already_booked"
    assert Booking.objects.count() == 1


def test_full_session_is_409(api, session):
    for _ in range(3):
        book_session(PatientFactory(), session.pk)

    response = _book(api, session)

    assert response.status_code == 409
    assert response.data["code"] == "session_full"


def test_unknown_session_is_404(api):
    response = api.post("/api/bookings/", {"session": 999_999}, format="json")

    assert response.status_code == 404
    assert response.data["code"] == "session_not_found"


@pytest.mark.parametrize(
    "payload", [{}, {"session": "abc"}, {"session": 1, "description": "x" * 501}]
)
def test_invalid_booking_payload_is_400(api, payload):
    assert api.post("/api/bookings/", payload, format="json").status_code == 400


def test_pay_twice_is_409(api, session):
    booking_id = _book(api, session).data["id"]
    api.post(f"/api/bookings/{booking_id}/pay/")

    response = api.post(f"/api/bookings/{booking_id}/pay/")

    assert response.status_code == 409
    assert response.data["code"] == "already_paid"


def test_cancel(api, session):
    booking_id = _book(api, session).data["id"]

    response = api.post(f"/api/bookings/{booking_id}/cancel/")

    assert response.status_code == 200
    assert response.data["status"] == "cancelled"
    assert api.get(f"/api/bookings/{booking_id}/queue/").data["state"] == "cancelled"


def test_list_shows_only_own_bookings_newest_session_first(api, patient, session):
    later = SessionFactory(date=TODAY + dt.timedelta(days=5))
    book_session(patient, session.pk)
    book_session(patient, later.pk)
    book_session(PatientFactory(), session.pk)

    response = api.get("/api/bookings/")

    assert [b["session"]["id"] for b in response.data] == [later.pk, session.pk]


@pytest.mark.parametrize("make", [lambda: DoctorFactory().user, lambda: HospitalFactory().user])
def test_staff_get_403(db, make):
    client = _api(make())

    assert client.get("/api/bookings/").status_code == 403
    assert client.post("/api/bookings/", {"session": 1}, format="json").status_code == 403


def test_bookings_need_login(db):
    assert APIClient().get("/api/bookings/").status_code == 401


def test_sessions_hide_past_and_count_seats_after_cancel(api, patient):
    doctor = DoctorFactory()
    SessionFactory(doctor=doctor, date=TODAY - dt.timedelta(days=1))
    upcoming = SessionFactory(doctor=doctor, capacity=2)
    later = SessionFactory(doctor=doctor, date=TODAY + dt.timedelta(days=2))
    mine = book_session(patient, upcoming.pk)
    book_session(PatientFactory(), upcoming.pk)
    cancel_booking(patient, mine)

    response = api.get(f"/api/doctors/{doctor.pk}/sessions/")

    assert [s["id"] for s in response.data] == [upcoming.pk, later.pk]
    assert response.data[0]["seats_left"] == 1
    assert set(response.data[0]) == {
        "id",
        "date",
        "start_time",
        "end_time",
        "fee",
        "capacity",
        "seats_left",
    }


def test_sessions_of_hidden_doctor_are_404(api):
    doctor = DoctorFactory(hospital=HospitalFactory(approval_status=ApprovalStatus.PENDING))
    SessionFactory(doctor=doctor)

    assert api.get(f"/api/doctors/{doctor.pk}/sessions/").status_code == 404


# ---- Hospital bookings page --------------------------------------------------------------------


def test_hospital_sees_its_doctors_bookings_for_a_date(client, db):
    hospital = HospitalFactory()
    mine = BookingFactory(session=SessionFactory(doctor=DoctorFactory(hospital=hospital)))
    BookingFactory(
        session=SessionFactory(doctor=mine.session.doctor, date=TODAY + dt.timedelta(days=3))
    )
    BookingFactory(session=SessionFactory())  # another hospital, same date
    client.force_login(hospital.user)

    response = client.get(f"/dashboard/hospital/bookings/?date={mine.session.date.isoformat()}")

    assert list(response.context["bookings"]) == [mine]


def test_hospital_bookings_default_to_today_and_ignore_bad_dates(client, db):
    hospital = HospitalFactory()
    today = BookingFactory(
        session=SessionFactory(doctor=DoctorFactory(hospital=hospital), date=TODAY),
        status=BookingStatus.COMPLETED,
    )
    client.force_login(hospital.user)

    assert list(client.get("/dashboard/hospital/bookings/").context["bookings"]) == [today]
    assert list(client.get("/dashboard/hospital/bookings/?date=nope").context["bookings"]) == [
        today
    ]


def test_pending_hospital_cannot_see_bookings(client, db):
    client.force_login(HospitalFactory(approval_status=ApprovalStatus.PENDING).user)

    response = client.get("/dashboard/hospital/bookings/")

    assert response.status_code == 302
    assert response.url == "/dashboard/pending/"
