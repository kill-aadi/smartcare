"""Payments. This module is the single seam a real gateway (Razorpay, Stripe, ...) would replace."""

from django.db import transaction

from accounts.models import User
from bookings.models import Booking, BookingStatus, PaymentStatus
from core.exceptions import AlreadyPaid, InvalidTransition, NotAllowed
from payments.models import Payment


@transaction.atomic
def pay_booking(patient: User, booking: Booking) -> Payment:
    """Simulate paying a booking's fee.

    The booking row is locked, so a double tap waits for the first payment and then gets
    ``AlreadyPaid`` instead of creating a second Payment.
    """
    booking = Booking.objects.select_for_update().select_related("session").get(pk=booking.pk)
    if booking.patient_id != patient.pk:
        raise NotAllowed("This isn't your booking.")
    if booking.status != BookingStatus.BOOKED:
        raise InvalidTransition("Only an active booking can be paid.")
    if booking.payment_status == PaymentStatus.PAID:
        raise AlreadyPaid("This booking is already paid.")
    payment = Payment.objects.create(booking=booking, payer=patient, amount=booking.session.fee)
    booking.payment_status = PaymentStatus.PAID
    booking.save(update_fields=["payment_status"])
    return payment
