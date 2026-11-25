"""Doctor dashboard routes, included under /dashboard/doctor/ in the dashboards namespace."""

from django.urls import path

from bookings import views
from bookings.queue import complete_booking, mark_no_show

urlpatterns = [
    path("sessions/", views.DoctorSessionsView.as_view(), name="doctor-sessions"),
    path("today/", views.DoctorTodayView.as_view(), name="doctor-today"),
    path("sessions/<int:pk>/queue/", views.QueuePanelView.as_view(), name="doctor-queue"),
    path("sessions/<int:pk>/call-next/", views.CallNextView.as_view(), name="doctor-call-next"),
    path(
        "bookings/<int:pk>/complete/",
        views.CloseBookingView.as_view(action=complete_booking),
        name="doctor-booking-complete",
    ),
    path(
        "bookings/<int:pk>/no-show/",
        views.CloseBookingView.as_view(action=mark_no_show),
        name="doctor-booking-no-show",
    ),
]
