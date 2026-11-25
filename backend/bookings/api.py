"""Patient booking API: sessions, book, cancel, pay (simulated) and live queue status."""

from dataclasses import asdict

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from bookings.models import Booking, BookingStatus
from bookings.queue import queue_status
from bookings.serializers import (
    BookingCreateSerializer,
    BookingSerializer,
    PaymentSerializer,
    QueueStatusSerializer,
    SessionSerializer,
)
from bookings.services import book_session, cancel_booking
from core.permissions import IsPatient
from doctors.models import Doctor
from payments.services import pay_booking


def upcoming_q(now=None) -> Q:
    """Sessions that haven't ended yet (dates and times are in TIME_ZONE)."""
    now = timezone.localtime(now)
    return Q(date__gt=now.date()) | Q(date=now.date(), end_time__gt=now.time())


class DoctorSessionListView(ListAPIView):
    """A visible doctor's sessions that haven't ended, soonest first, with seats left."""

    permission_classes = [IsPatient]
    serializer_class = SessionSerializer
    pagination_class = None

    def get_queryset(self):
        doctor = get_object_or_404(Doctor.objects.visible_to_patients(), pk=self.kwargs["pk"])
        return (
            doctor.sessions.filter(upcoming_q())
            .annotate(
                active_bookings=Count(
                    "bookings", filter=~Q(bookings__status=BookingStatus.CANCELLED)
                )
            )
            .order_by("date", "start_time")
        )


class _OwnBookingMixin:
    """Every booking lookup is filtered by the patient, so other people's bookings are 404."""

    permission_classes = [IsPatient]
    serializer_class = BookingSerializer

    def get_queryset(self):
        return Booking.objects.filter(patient=self.request.user).select_related(
            "session__doctor__specialization", "session__doctor__hospital"
        )

    def own_booking(self) -> Booking:
        return get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])


class BookingListCreateView(_OwnBookingMixin, ListAPIView):
    def get_queryset(self):
        return super().get_queryset().order_by("-session__date", "-session__start_time")

    @extend_schema(request=BookingCreateSerializer, responses={201: BookingSerializer})
    def post(self, request):
        data = BookingCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        booking = book_session(
            request.user, data.validated_data["session"], data.validated_data.get("description", "")
        )
        booking = self.get_queryset().get(pk=booking.pk)
        return Response(self.get_serializer(booking).data, status=status.HTTP_201_CREATED)


class BookingDetailView(_OwnBookingMixin, RetrieveAPIView):
    def get_object(self):
        return self.own_booking()


class BookingCancelView(_OwnBookingMixin, GenericAPIView):
    @extend_schema(request=None, responses=BookingSerializer)
    def post(self, request, pk):
        booking = cancel_booking(request.user, self.own_booking())
        return Response(self.get_serializer(self.get_queryset().get(pk=booking.pk)).data)


class BookingPayView(_OwnBookingMixin, GenericAPIView):
    serializer_class = PaymentSerializer

    @extend_schema(
        request=None,
        responses=PaymentSerializer,
        description="Simulated payment: no money moves (ADR 0008).",
    )
    def post(self, request, pk):
        return Response(PaymentSerializer(pay_booking(request.user, self.own_booking())).data)


class BookingQueueView(_OwnBookingMixin, GenericAPIView):
    """Polled by the app every ~15 s. One booking+session query plus one count: cheap to cache."""

    serializer_class = QueueStatusSerializer

    def get(self, request, pk):
        booking = get_object_or_404(
            Booking.objects.filter(patient=request.user).select_related("session"), pk=pk
        )
        return Response(QueueStatusSerializer(asdict(queue_status(booking))).data)
