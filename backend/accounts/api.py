from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.serializers import MeSerializer, PatientRegisterSerializer, PatientTokenSerializer
from accounts.services import register_patient
from core.permissions import IsPatient


class PatientRegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=PatientRegisterSerializer, responses={201: None})
    def post(self, request):
        serializer = PatientRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = register_patient(**serializer.validated_data)
        return Response({"id": user.id, "email": user.email}, status=status.HTTP_201_CREATED)


class PatientTokenView(TokenObtainPairView):
    serializer_class = PatientTokenSerializer


class MeView(APIView):
    permission_classes = [IsPatient]

    @extend_schema(responses=MeSerializer)
    def get(self, request):
        return Response(MeSerializer(request.user.patient_profile).data)
