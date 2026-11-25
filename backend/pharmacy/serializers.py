from rest_framework import serializers

from pharmacy.models import Pharmacy


class PharmacySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Pharmacy
        fields = ["id", "name", "phone"]
