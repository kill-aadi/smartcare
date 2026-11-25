"""Doctor dashboard pages: consulting sessions and today's live queue."""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, TemplateView

from accounts.models import Role
from bookings.forms import SessionForm
from bookings.models import Booking, BookingStatus
from bookings.queue import call_next, complete_booking
from bookings.services import create_session
from core.exceptions import DomainError
from dashboards.mixins import RoleRequiredMixin


class DoctorRequiredMixin(RoleRequiredMixin):
    allowed_roles = (Role.DOCTOR,)

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == Role.DOCTOR:
            self.doctor = request.user.doctor
        return super().dispatch(request, *args, **kwargs)


class DoctorSessionsView(DoctorRequiredMixin, FormView):
    """Upcoming sessions plus the "add a session" form on one page."""

    template_name = "dashboards/doctor/sessions.html"
    form_class = SessionForm

    def get_context_data(self, **kwargs):
        now = timezone.localtime()
        upcoming = Q(date__gt=now.date()) | Q(date=now.date(), end_time__gt=now.time())
        kwargs["sessions"] = self.doctor.sessions.filter(upcoming)
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        try:
            create_session(self.doctor, **form.cleaned_data)
        except DomainError as error:
            form.add_error(None, str(error))
            return self.form_invalid(form)
        messages.success(self.request, "Session added.")
        return redirect("dashboards:doctor-sessions")


# ---- Today's queue (HTMX) ----------------------------------------------------------------------

PANEL_TEMPLATE = "dashboards/doctor/_queue_panel.html"
WAITING_SHOWN = 5


def _panel_context(session, error: str = "") -> dict:
    waiting = session.bookings.filter(
        status=BookingStatus.BOOKED, token_no__gt=session.current_token
    ).order_by("token_no")
    return {
        "session": session,
        "serving": session.bookings.filter(token_no=session.current_token).first(),
        "waiting": waiting[:WAITING_SHOWN],
        "waiting_count": waiting.count(),
        "error": error,
    }


class DoctorTodayView(DoctorRequiredMixin, TemplateView):
    template_name = "dashboards/doctor/today.html"

    def get_context_data(self, **kwargs):
        sessions = self.doctor.sessions.filter(date=timezone.localdate())
        kwargs["panels"] = [_panel_context(session) for session in sessions]
        kwargs["sessions"] = sessions
        return super().get_context_data(**kwargs)


class QueuePanelView(DoctorRequiredMixin, View):
    """GET: the panel the page polls every 5 s. POST subclasses act, then return the panel."""

    def session_for(self, pk):
        return get_object_or_404(self.doctor.sessions, pk=pk)  # another doctor's -> 404

    def panel(self, session, error=""):
        session.refresh_from_db()
        return render(self.request, PANEL_TEMPLATE, _panel_context(session, error))

    def get(self, request, pk):
        return self.panel(self.session_for(pk))


class CallNextView(QueuePanelView):
    def post(self, request, pk):
        session = self.session_for(pk)
        try:
            called = call_next(self.doctor, session)
        except DomainError as error:
            return self.panel(session, str(error))
        return self.panel(session, "" if called else "Nobody left to call.")


class CloseBookingView(QueuePanelView):
    action = staticmethod(complete_booking)

    def post(self, request, pk):
        booking = get_object_or_404(
            Booking.objects.filter(session__doctor=self.doctor).select_related("session"), pk=pk
        )
        try:
            self.action(self.doctor, booking)
        except DomainError as error:
            return self.panel(booking.session, str(error))
        return self.panel(booking.session)
