"""Everything under /api/: the REST API used by the patient app."""

from django.urls import include, path

from doctors import api as doctors_api
from hospitals import api as hospitals_api

urlpatterns = [
    path("", include("accounts.urls")),
    path("specializations/", doctors_api.SpecializationListView.as_view()),
    path("doctors/", doctors_api.DoctorListView.as_view()),
    path("hospitals/", hospitals_api.HospitalListView.as_view()),
    path("hospitals/<int:pk>/", hospitals_api.HospitalDetailView.as_view()),
    path("hospitals/<int:pk>/pharmacies/", hospitals_api.HospitalPharmacyListView.as_view()),
]
