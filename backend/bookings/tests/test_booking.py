import datetime as dt

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from bookings.models import Booking, BookingStatus, PaymentStatus
from bookings.services import (
    AlreadyBooked,
    SessionFull,
    SessionInPast,
    SessionNotFound,
    book_session,
    cancel_booking,
    seats_left,
)
from core.exceptions import NotAllowed
from core.factories import DoctorFactory, HospitalFactory, PatientFactory, SessionFactory
from hospitals.models import ApprovalStatus


@pytest.fixture
def session(db):
    return SessionFactory(capacity=2)


def test_tokens_are_sequential_per_session(session):
    first = book_session(PatientFactory(), session.pk, "Fever for two days")
    second = book_session(PatientFactory(), session.pk)

    assert (first.token_no, second.token_no) == (1, 2)
    assert first.description == "Fever for two days"
    assert first.status == BookingStatus.BOOKED
    assert first.payment_status == PaymentStatus.PENDING


def test_each_session_counts_tokens_from_one(session):
    book_session(PatientFactory(), session.pk)

    other = book_session(
        PatientFactory(),
        SessionFactory(doctor=session.doctor, start_time=dt.time(13), end_time=dt.time(14)).pk,
    )

    assert other.token_no == 1


def test_same_patient_booking_twice_is_rejected(session):
    patient = PatientFactory()
    book_session(patient, session.pk)

    with pytest.raises(AlreadyBooked):
        book_session(patient, session.pk)

    assert session.bookings.count() == 1


def test_full_session_is_rejected(session):
    book_session(PatientFactory(), session.pk)
    book_session(PatientFactory(), session.pk)

    with pytest.raises(SessionFull):
        book_session(PatientFactory(), session.pk)

    assert session.bookings.count() == 2


def test_past_session_is_rejected(db):
    session = SessionFactory(date=timezone.localdate() - dt.timedelta(days=1))

    with pytest.raises(SessionInPast):
        book_session(PatientFactory(), session.pk)


def test_session_ending_now_is_rejected(db):
    session = SessionFactory()
    with pytest.raises(SessionInPast):
        book_session(PatientFactory(), session.pk, now=session.ends_at())


@pytest.mark.parametrize("status", [ApprovalStatus.PENDING, ApprovalStatus.REJECTED])
def test_session_of_unapproved_hospital_is_not_found(db, status):
    doctor = DoctorFactory(hospital=HospitalFactory(approval_status=status))
    session = SessionFactory(doctor=doctor)

    with pytest.raises(SessionNotFound):
        book_session(PatientFactory(), session.pk)


def test_session_of_deactivated_doctor_is_not_found(db):
    session = SessionFactory()
    session.doctor.user.is_active = False
    session.doctor.user.save()

    with pytest.raises(SessionNotFound):
        book_session(PatientFactory(), session.pk)


def test_missing_session_is_not_found(db):
    with pytest.raises(SessionNotFound):
        book_session(PatientFactory(), 999_999)


def test_cancel_frees_the_seat_but_never_reuses_the_token(session):
    first_patient = PatientFactory()
    first = book_session(first_patient, session.pk)
    book_session(PatientFactory(), session.pk)

    cancel_booking(first_patient, first)
    third = book_session(PatientFactory(), session.pk)

    first.refresh_from_db()
    assert first.status == BookingStatus.CANCELLED
    assert third.token_no == 3


def test_cancelled_patient_may_book_again(db):
    session = SessionFactory(capacity=5)
    patient = PatientFactory()
    first = book_session(patient, session.pk)
    book_session(PatientFactory(), session.pk)
    cancel_booking(patient, first)
    book_session(PatientFactory(), session.pk)

    again = book_session(patient, session.pk)

    assert again.token_no == 4


def test_seats_left_ignores_cancelled_bookings(session):
    patient = PatientFactory()
    booking = book_session(patient, session.pk)
    assert seats_left(session) == 1

    cancel_booking(patient, booking)

    assert seats_left(session) == 2


def test_cannot_cancel_someone_elses_booking(session):
    booking = book_session(PatientFactory(), session.pk)

    with pytest.raises(NotAllowed):
        cancel_booking(PatientFactory(), booking)


def test_cannot_cancel_twice(session):
    patient = PatientFactory()
    booking = book_session(patient, session.pk)
    cancel_booking(patient, booking)

    with pytest.raises(NotAllowed):
        cancel_booking(patient, booking)


def test_cannot_cancel_after_the_session_ends(session):
    patient = PatientFactory()
    booking = book_session(patient, session.pk)

    with pytest.raises(NotAllowed):
        cancel_booking(patient, booking, now=session.ends_at())


def test_database_allows_one_active_booking_per_patient(session):
    patient = PatientFactory()
    book_session(patient, session.pk)

    with pytest.raises(IntegrityError), transaction.atomic():
        Booking.objects.create(session=session, patient=patient, token_no=9)


def test_database_rejects_duplicate_token(session):
    book_session(PatientFactory(), session.pk)

    with pytest.raises(IntegrityError), transaction.atomic():
        Booking.objects.create(session=session, patient=PatientFactory(), token_no=1)
