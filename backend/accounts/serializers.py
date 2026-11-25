from django.contrib.auth.password_validation import validate_password
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from accounts.models import DUPLICATE_EMAIL_MESSAGE, Gender, PatientProfile, Role, User

STAFF_ON_APP_MESSAGE = "This app is for patients. Staff should use the web dashboard."


class PatientRegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    name = serializers.CharField(max_length=120)
    phone = serializers.CharField(max_length=30)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=Gender.choices)
    place = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(DUPLICATE_EMAIL_MESSAGE)
        return value

    def validate(self, attrs):
        try:
            validate_password(attrs["password"], User(email=attrs.get("email", "")))
        except Exception as error:  # django ValidationError -> DRF field error
            raise serializers.ValidationError({"password": list(error.messages)}) from error
        return attrs


class PatientTokenSerializer(TokenObtainPairSerializer):
    """Issue tokens to patients only; staff credentials get a clear message and no token."""

    def validate(self, attrs):
        data = super().validate(attrs)  # raises 401 for wrong credentials / inactive users
        if self.user.role != Role.PATIENT:
            raise exceptions.AuthenticationFailed(STAFF_ON_APP_MESSAGE, code="not_a_patient")
        return data


class MeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="user.id")
    email = serializers.EmailField(source="user.email")

    class Meta:
        model = PatientProfile
        fields = ["id", "email", "name", "phone", "date_of_birth", "gender", "place"]
