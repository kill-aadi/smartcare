from rest_framework import serializers


class LocationQuerySerializer(serializers.Serializer):
    """Optional ``?lat=&lng=`` query parameters: both or neither, within valid ranges."""

    lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    lng = serializers.FloatField(required=False, min_value=-180, max_value=180)

    def validate(self, attrs):
        if ("lat" in attrs) != ("lng" in attrs):
            raise serializers.ValidationError("Give both lat and lng, or neither.")
        return attrs


def photo_url(request, image) -> str | None:
    return request.build_absolute_uri(image.url) if image else None
