"""Doctor dashboard pages for consulting sessions."""

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import FormView

from accounts.models import Role
from bookings.forms import SessionForm
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
