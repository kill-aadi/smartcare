"""Doctor dashboard routes, included under /dashboard/doctor/ in the dashboards namespace."""

from django.urls import path

from bookings import views

urlpatterns = [
    path("sessions/", views.DoctorSessionsView.as_view(), name="doctor-sessions"),
]
