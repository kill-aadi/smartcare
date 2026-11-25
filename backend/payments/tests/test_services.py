import re
from decimal import Decimal

import pytest

from bookings.models import BookingStatus, PaymentStatus
from core.exceptions import AlreadyPaid, InvalidTransition, NotAllowed
from core.factories import BookingFactory, PatientFactory, SessionFactory
from payments.models import Payment
from payments.services import pay_booking


@pytest.fixture
def booking(db):
    return BookingFactory(session=SessionFactory(fee=Decimal("450.00")))


def test_paying_records_a_simulated_payment(booking):
    payment = pay_booking(booking.patient, booking)

    booking.refresh_from_db()
    assert booking.payment_status == PaymentStatus.PAID
    assert payment.amount == Decimal("450.00")
    assert payment.payer == booking.patient
    assert payment.booking == booking
    assert payment.provider == "simulated"
    assert re.fullmatch(r"SIM-[0-9A-F]{12}", payment.reference)


def test_paying_twice_is_rejected_and_records_one_payment(booking):
    pay_booking(booking.patient, booking)

    with pytest.raises(AlreadyPaid):
        pay_booking(booking.patient, booking)

    assert Payment.objects.count() == 1


def test_payment_references_are_unique(db):
    refs = {pay_booking(b.patient, b).reference for b in BookingFactory.create_batch(5)}

    assert len(refs) == 5


@pytest.mark.parametrize("status", [BookingStatus.CANCELLED, BookingStatus.NO_SHOW])
def test_paying_a_closed_booking_is_rejected(db, status):
    booking = BookingFactory(status=status)

    with pytest.raises(InvalidTransition):
        pay_booking(booking.patient, booking)

    assert not Payment.objects.exists()


def test_paying_someone_elses_booking_is_not_allowed(booking):
    with pytest.raises(NotAllowed):
        pay_booking(PatientFactory(), booking)

    booking.refresh_from_db()
    assert booking.payment_status == PaymentStatus.PENDING
