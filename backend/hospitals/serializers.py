from rest_framework import serializers

from core.serializers import photo_url
from hospitals.models import Hospital


class HospitalSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()
    # Filled in by the view when the patient shares a location; otherwise null.
    distance_km = serializers.SerializerMethodField()
    straight_line_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Hospital
        fields = [
            "id",
            "name",
            "place",
            "phone",
            "email",
            "photo_url",
            "latitude",
            "longitude",
            "distance_km",
            "straight_line_minutes",
        ]

    def get_photo_url(self, hospital) -> str | None:
        return photo_url(self.context["request"], hospital.photo)

    def get_distance_km(self, hospital) -> float | None:
        km = getattr(hospital, "distance_km", None)
        return None if km is None else round(km, 1)

    def get_straight_line_minutes(self, hospital) -> int | None:
        return getattr(hospital, "straight_line_minutes", None)
