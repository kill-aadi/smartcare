from django.urls import include, path

from dashboards import views
from doctors import views as doctor_views
from hospitals.models import ApprovalStatus
from pharmacy import views as pharmacy_views

app_name = "dashboards"

urlpatterns = [
    path("", views.dashboard_root, name="root"),
    path("use-the-app/", views.PatientUseAppView.as_view(), name="patient-use-app"),
    path(
        "pending/",
        views.HospitalStatusView.as_view(
            template_name="dashboards/pending.html", expected_status=ApprovalStatus.PENDING
        ),
        name="pending",
    ),
    path(
        "rejected/",
        views.HospitalStatusView.as_view(
            template_name="dashboards/rejected.html", expected_status=ApprovalStatus.REJECTED
        ),
        name="rejected",
    ),
    path("admin/", views.AdminHomeView.as_view(), name="admin-home"),
    path("admin/hospitals/", views.AdminHospitalListView.as_view(), name="admin-hospitals"),
    path(
        "admin/hospitals/<int:pk>/",
        views.AdminHospitalDetailView.as_view(),
        name="admin-hospital-detail",
    ),
    path(
        "admin/hospitals/<int:pk>/licence/",
        views.AdminLicenceView.as_view(),
        name="admin-hospital-licence",
    ),
    path("admin/users/", views.AdminUserListView.as_view(), name="admin-users"),
    path("hospital/", views.HospitalHomeView.as_view(), name="hospital-home"),
    path(
        "hospital/doctors/",
        doctor_views.HospitalDoctorListView.as_view(),
        name="hospital-doctors",
    ),
    path(
        "hospital/doctors/new/",
        doctor_views.HospitalDoctorCreateView.as_view(),
        name="hospital-doctor-new",
    ),
    path(
        "hospital/doctors/<int:pk>/",
        doctor_views.HospitalDoctorUpdateView.as_view(),
        name="hospital-doctor-edit",
    ),
    path(
        "hospital/doctors/<int:pk>/active/",
        doctor_views.HospitalDoctorToggleActiveView.as_view(),
        name="hospital-doctor-active",
    ),
    path(
        "hospital/pharmacies/",
        pharmacy_views.HospitalPharmacyListView.as_view(),
        name="hospital-pharmacies",
    ),
    path(
        "hospital/pharmacies/new/",
        pharmacy_views.HospitalPharmacyCreateView.as_view(),
        name="hospital-pharmacy-new",
    ),
    path("doctor/", views.DoctorHomeView.as_view(), name="doctor-home"),
    path("doctor/", include("bookings.urls")),
    path("pharmacy/", views.PharmacyHomeView.as_view(), name="pharmacy-home"),
]
