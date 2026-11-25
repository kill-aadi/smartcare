from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import ListAPIView, RetrieveAPIView

from core.geo import haversine_km, straight_line_minutes
from core.permissions import IsPatient
from core.serializers import LocationQuerySerializer
from hospitals.models import Hospital
from hospitals.serializers import HospitalSerializer
from pharmacy.serializers import PharmacySummarySerializer

MAX_RESULTS = 50


@extend_schema(
    parameters=[
        OpenApiParameter("search", str, description="Matches name or place"),
        OpenApiParameter("lat", float),
        OpenApiParameter("lng", float),
    ]
)
class HospitalListView(ListAPIView):
    """Approved hospitals. With ``lat``/``lng`` they're sorted nearest first."""

    permission_classes = [IsPatient]
    serializer_class = HospitalSerializer

    def list(self, request, *args, **kwargs):
        self.location = LocationQuerySerializer(data=request.query_params)
        self.location.is_valid(raise_exception=True)
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        hospitals = Hospital.objects.approved()
        search = self.request.query_params.get("search", "").strip()
        if search:
            hospitals = hospitals.filter(Q(name__icontains=search) | Q(place__icontains=search))
        here = self.location.validated_data
        if not here:
            return list(hospitals[:MAX_RESULTS])

        # Distance for every matching hospital from just (id, lat, lng), then load the nearest 50.
        # Plain Python: easy to explain, fine for thousands of rows, no PostGIS needed.
        distances = {
            pk: haversine_km(here["lat"], here["lng"], float(lat), float(lng))
            for pk, lat, lng in hospitals.values_list("pk", "latitude", "longitude")
        }
        nearest = sorted(distances, key=distances.get)[:MAX_RESULTS]
        result = list(hospitals.filter(pk__in=nearest))
        for h in result:
            h.distance_km = distances[h.pk]
            h.straight_line_minutes = straight_line_minutes(h.distance_km)
        result.sort(key=lambda h: h.distance_km)
        return result


class HospitalDetailView(RetrieveAPIView):
    permission_classes = [IsPatient]
    serializer_class = HospitalSerializer
    queryset = Hospital.objects.approved()


class HospitalPharmacyListView(ListAPIView):
    permission_classes = [IsPatient]
    serializer_class = PharmacySummarySerializer

    def get_queryset(self):
        hospital = get_object_or_404(Hospital.objects.approved(), pk=self.kwargs["pk"])
        return hospital.pharmacies.all()
