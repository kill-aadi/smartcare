from rest_framework import serializers

from core.serializers import photo_url
from doctors.models import Doctor, Specialization
from hospitals.models import Hospital


class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialization
        fields = ["id", "name", "description"]


class SpecializationRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialization
        fields = ["id", "name"]


class HospitalRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = ["id", "name", "place", "latitude", "longitude"]


class DoctorSerializer(serializers.ModelSerializer):
    specialization = SpecializationRefSerializer()
    hospital = HospitalRefSerializer()
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            "id",
            "name",
            "specialization",
            "qualification",
            "experience_years",
            "gender",
            "photo_url",
            "hospital",
        ]

    def get_photo_url(self, doctor) -> str | None:
        return photo_url(self.context["request"], doctor.photo)
