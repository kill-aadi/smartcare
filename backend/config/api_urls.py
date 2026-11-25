"""Everything under /api/: the REST API used by the patient app."""

from django.urls import include, path

urlpatterns = [
    path("", include("accounts.urls")),
]
