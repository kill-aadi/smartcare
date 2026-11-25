from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.generics import ListAPIView

from core.permissions import IsPatient
from doctors.models import Doctor, Specialization
from doctors.serializers import DoctorSerializer, SpecializationSerializer

MAX_RESULTS = 50


class SpecializationListView(ListAPIView):
    permission_classes = [IsPatient]
    serializer_class = SpecializationSerializer
    queryset = Specialization.objects.all()


class _DoctorFilters(serializers.Serializer):
    specialization = serializers.IntegerField(required=False, min_value=1)
    hospital = serializers.IntegerField(required=False, min_value=1)


@extend_schema(
    parameters=[OpenApiParameter("specialization", int), OpenApiParameter("hospital", int)]
)
class DoctorListView(ListAPIView):
    """Doctors patients may book: active, at approved hospitals."""

    permission_classes = [IsPatient]
    serializer_class = DoctorSerializer

    def get_queryset(self):
        filters = _DoctorFilters(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        doctors = Doctor.objects.visible_to_patients().select_related("specialization", "hospital")
        if "specialization" in filters.validated_data:
            doctors = doctors.filter(specialization_id=filters.validated_data["specialization"])
        if "hospital" in filters.validated_data:
            doctors = doctors.filter(hospital_id=filters.validated_data["hospital"])
        return doctors[:MAX_RESULTS]
