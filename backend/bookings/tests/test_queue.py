import datetime as dt

import pytest
from django.utils import timezone

from bookings.models import BookingStatus
from bookings.queue import (
    NotToday,
    QueueStatus,
    call_next,
    complete_booking,
    mark_no_show,
    queue_status,
)
from core.exceptions import InvalidTransition, NotAllowed
from core.factories import BookingFactory, DoctorFactory, PatientFactory, SessionFactory

DAY = dt.date(2030, 1, 15)


@pytest.fixture
def session(db):
    return SessionFactory(date=DAY)


def _tokens(session, *numbers, **kw):
    return [BookingFactory(session=session, token_no=n, **kw) for n in numbers]


def test_call_next_skips_cancelled_and_stops_when_nobody_is_left(session):
    one, two, three = _tokens(session, 1, 2, 3)
    two.status = BookingStatus.CANCELLED
    two.save()

    called = [call_next(session.doctor, session, today=DAY) for _ in range(3)]

    session.refresh_from_db()
    assert called == [1, 3, None]
    assert session.current_token == 3


def test_call_next_on_an_empty_session_changes_nothing(session):
    assert call_next(session.doctor, session, today=DAY) is None

    session.refresh_from_db()
    assert session.current_token == 0


def test_call_next_on_another_doctors_session_is_not_allowed(session):
    _tokens(session, 1)

    with pytest.raises(NotAllowed):
        call_next(DoctorFactory(), session, today=DAY)


def test_call_next_only_on_the_sessions_day(session):
    _tokens(session, 1)

    with pytest.raises(NotToday):
        call_next(session.doctor, session, today=DAY - dt.timedelta(days=1))


@pytest.mark.parametrize(
    ("action", "status"),
    [(complete_booking, BookingStatus.COMPLETED), (mark_no_show, BookingStatus.NO_SHOW)],
)
def test_called_token_can_be_completed_or_marked_no_show(session, action, status):
    booking, _ = _tokens(session, 1, 2)
    call_next(session.doctor, session, today=DAY)

    action(session.doctor, booking)

    booking.refresh_from_db()
    assert booking.status == status


@pytest.mark.parametrize("action", [complete_booking, mark_no_show])
def test_not_yet_called_token_cannot_be_closed(session, action):
    _, later = _tokens(session, 1, 2)
    call_next(session.doctor, session, today=DAY)

    with pytest.raises(InvalidTransition):
        action(session.doctor, later)


@pytest.mark.parametrize("action", [complete_booking, mark_no_show])
def test_closed_or_cancelled_booking_cannot_be_closed_again(session, action):
    (booking,) = _tokens(session, 1)
    call_next(session.doctor, session, today=DAY)
    complete_booking(session.doctor, booking)

    with pytest.raises(InvalidTransition):
        action(session.doctor, booking)


@pytest.mark.parametrize("action", [complete_booking, mark_no_show])
def test_other_doctor_cannot_close_a_booking(session, action):
    (booking,) = _tokens(session, 1)
    call_next(session.doctor, session, today=DAY)

    with pytest.raises(NotAllowed):
        action(DoctorFactory(), booking)


# ---- queue_status ------------------------------------------------------------------------------


def _status_of(token_no, current_token, avg=10, **booking_fields):
    session = SessionFactory(current_token=current_token, avg_consult_minutes=avg)
    return queue_status(BookingFactory(session=session, token_no=token_no, **booking_fields))


def test_waiting_patient_gets_eta(db):
    assert _status_of(7, 4) == QueueStatus(
        token_no=7, current_token=4, ahead=0, eta_minutes=30, state="waiting"
    )


def test_now_serving(db):
    status = _status_of(4, 4)

    assert (status.state, status.eta_minutes) == ("now_serving", 0)


def test_token_already_passed_is_done(db):
    status = _status_of(2, 4)

    assert (status.state, status.eta_minutes) == ("done", 0)


@pytest.mark.parametrize("booking_status", [BookingStatus.COMPLETED, BookingStatus.NO_SHOW])
def test_closed_booking_is_done(db, booking_status):
    assert _status_of(4, 4, status=booking_status).state == "done"


def test_cancelled_booking(db):
    assert _status_of(7, 4, status=BookingStatus.CANCELLED).state == "cancelled"


def test_ahead_counts_only_active_bookings_between(db):
    session = SessionFactory(current_token=4)
    _tokens(session, 3, 4, 5, 6)  # 3 and 4 are not ahead: already called
    _tokens(session, 8, 9)  # behind
    cancelled = BookingFactory(session=session, token_no=7, status=BookingStatus.CANCELLED)
    mine = BookingFactory(session=session, token_no=10)

    status = queue_status(mine)

    assert status.ahead == 4  # 5, 6, 8, 9
    assert cancelled.pk


# ---- Doctor "Today" page -----------------------------------------------------------------------


@pytest.fixture
def today_session(db):
    session = SessionFactory(
        date=timezone.localdate(), start_time=dt.time(0, 0), end_time=dt.time(23, 59)
    )
    _tokens(session, 1, 2)
    return session


@pytest.fixture
def doctor_client(client, today_session):
    client.force_login(today_session.doctor.user)
    return client


def test_today_page_lists_only_todays_sessions(doctor_client, today_session):
    SessionFactory(doctor=today_session.doctor)  # tomorrow

    response = doctor_client.get("/dashboard/doctor/today/")

    assert list(response.context["sessions"]) == [today_session]
    assert b'hx-trigger="every 5s"' in response.content


def test_queue_panel_is_a_fragment(doctor_client, today_session):
    response = doctor_client.get(f"/dashboard/doctor/sessions/{today_session.pk}/queue/")

    assert response.status_code == 200
    assert b"<html" not in response.content
    assert b"Now serving" in response.content


def test_call_next_over_htmx_returns_the_updated_panel(doctor_client, today_session):
    response = doctor_client.post(
        f"/dashboard/doctor/sessions/{today_session.pk}/call-next/", HTTP_HX_REQUEST="true"
    )

    assert response.status_code == 200
    assert b"<html" not in response.content
    assert b"Now serving 1" in response.content
    today_session.refresh_from_db()
    assert today_session.current_token == 1


def test_complete_from_the_panel(doctor_client, today_session):
    doctor_client.post(f"/dashboard/doctor/sessions/{today_session.pk}/call-next/")
    booking = today_session.bookings.get(token_no=1)

    response = doctor_client.post(f"/dashboard/doctor/bookings/{booking.pk}/complete/")

    booking.refresh_from_db()
    assert booking.status == BookingStatus.COMPLETED
    assert b"<html" not in response.content


def test_panel_shows_service_errors(doctor_client, today_session):
    booking = today_session.bookings.get(token_no=2)  # not called yet

    response = doctor_client.post(f"/dashboard/doctor/bookings/{booking.pk}/no-show/")

    assert response.status_code == 200
    assert b"alert-danger" in response.content


def test_another_doctors_queue_is_404(client, today_session):
    client.force_login(DoctorFactory().user)

    assert client.get(f"/dashboard/doctor/sessions/{today_session.pk}/queue/").status_code == 404
    assert (
        client.post(f"/dashboard/doctor/sessions/{today_session.pk}/call-next/").status_code == 404
    )
    booking = today_session.bookings.first()
    assert client.post(f"/dashboard/doctor/bookings/{booking.pk}/complete/").status_code == 404


def test_today_page_is_doctor_only(client, db):
    client.force_login(PatientFactory())

    assert client.get("/dashboard/doctor/today/").status_code == 403
