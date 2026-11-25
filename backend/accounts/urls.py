from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts import api

urlpatterns = [
    path("auth/register/", api.PatientRegisterView.as_view(), name="api-register"),
    path("auth/token/", api.PatientTokenView.as_view(), name="api-token"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="api-token-refresh"),
    path("me/", api.MeView.as_view(), name="api-me"),
]
