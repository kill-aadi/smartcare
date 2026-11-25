from rest_framework import serializers

from bookings.models import Booking, ConsultingSession
from bookings.services import seats_left
from doctors.models import Doctor
from doctors.serializers import SpecializationRefSerializer
from hospitals.models import Hospital
from payments.models import Payment


class SessionSerializer(serializers.ModelSerializer):
    seats_left = serializers.SerializerMethodField()

    class Meta:
        model = ConsultingSession
        fields = ["id", "date", "start_time", "end_time", "fee", "capacity", "seats_left"]

    def get_seats_left(self, session) -> int:
        active = getattr(session, "active_bookings", None)  # annotated by the list view
        return seats_left(session) if active is None else max(session.capacity - active, 0)


class BookingCreateSerializer(serializers.Serializer):
    session = serializers.IntegerField(min_value=1)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)


class _SessionRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultingSession
        fields = ["id", "date", "start_time", "end_time", "fee"]


class _DoctorRefSerializer(serializers.ModelSerializer):
    specialization = SpecializationRefSerializer()

    class Meta:
        model = Doctor
        fields = ["id", "name", "specialization"]


class _HospitalRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = ["id", "name", "latitude", "longitude"]


class BookingSerializer(serializers.ModelSerializer):
    session = _SessionRefSerializer()
    doctor = _DoctorRefSerializer(source="session.doctor")
    hospital = _HospitalRefSerializer(source="session.doctor.hospital")
    has_prescription = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
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
        ]

    def get_has_prescription(self, booking) -> bool:
        # The 1:1 Prescription arrives in milestone 4; until then nothing has one.
        return hasattr(booking, "prescription")


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["reference", "amount", "provider"]


class QueueStatusSerializer(serializers.Serializer):
    token_no = serializers.IntegerField()
    current_token = serializers.IntegerField()
    ahead = serializers.IntegerField()
    eta_minutes = serializers.IntegerField(
        help_text="Estimate only: tokens to go × average minutes."
    )
    state = serializers.ChoiceField(choices=["waiting", "now_serving", "done", "cancelled"])
