from django.urls import path

from dashboards import views
from hospitals.models import ApprovalStatus

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
    path("doctor/", views.DoctorHomeView.as_view(), name="doctor-home"),
    path("pharmacy/", views.PharmacyHomeView.as_view(), name="pharmacy-home"),
]
