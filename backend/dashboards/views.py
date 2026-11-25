from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from accounts.models import Role, User
from core.exceptions import DomainError
from dashboards.mixins import ApprovedHospitalRequiredMixin, RoleRequiredMixin
from hospitals.models import ApprovalStatus, Hospital
from hospitals.services import approve_hospital, reject_hospital

ROLE_HOME = {
    Role.ADMIN: "dashboards:admin-home",
    Role.HOSPITAL: "dashboards:hospital-home",
    Role.DOCTOR: "dashboards:doctor-home",
    Role.PHARMACY: "dashboards:pharmacy-home",
    Role.PATIENT: "dashboards:patient-use-app",
}


@login_required
def dashboard_root(request):
    """Send each user to their own role's dashboard."""
    return redirect(ROLE_HOME[request.user.role])


class PatientUseAppView(RoleRequiredMixin, TemplateView):
    allowed_roles = (Role.PATIENT,)
    template_name = "dashboards/patient_use_app.html"


class HospitalStatusView(RoleRequiredMixin, TemplateView):
    """The page a pending or rejected hospital sees instead of its dashboard."""

    allowed_roles = (Role.HOSPITAL,)
    expected_status: str = ApprovalStatus.PENDING

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if (
            request.user.is_authenticated
            and request.user.role == Role.HOSPITAL
            and request.user.hospital.approval_status != self.expected_status
        ):
            return redirect("dashboards:root")
        return response

    def get_context_data(self, **kwargs):
        return super().get_context_data(hospital=self.request.user.hospital, **kwargs)


# ---- Role homes -------------------------------------------------------------------------------


class AdminHomeView(RoleRequiredMixin, TemplateView):
    allowed_roles = (Role.ADMIN,)
    template_name = "dashboards/admin/home.html"

    def get_context_data(self, **kwargs):
        pending = Hospital.objects.filter(approval_status=ApprovalStatus.PENDING).count()
        return super().get_context_data(pending_count=pending, **kwargs)


class HospitalHomeView(ApprovedHospitalRequiredMixin, TemplateView):
    template_name = "dashboards/hospital/home.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(hospital=self.hospital, **kwargs)


class DoctorHomeView(RoleRequiredMixin, TemplateView):
    allowed_roles = (Role.DOCTOR,)
    template_name = "dashboards/doctor/home.html"


class PharmacyHomeView(RoleRequiredMixin, TemplateView):
    allowed_roles = (Role.PHARMACY,)
    template_name = "dashboards/pharmacy/home.html"


# ---- Admin: hospital approvals and users -------------------------------------------------------


class AdminHospitalListView(RoleRequiredMixin, ListView):
    allowed_roles = (Role.ADMIN,)
    template_name = "dashboards/admin/hospitals.html"
    context_object_name = "hospitals"

    def get_queryset(self):
        hospitals = Hospital.objects.order_by("-created_at")
        status = self.request.GET.get("status")
        if status in ApprovalStatus.values:
            hospitals = hospitals.filter(approval_status=status)
        return hospitals

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            statuses=ApprovalStatus.choices, current=self.request.GET.get("status", ""), **kwargs
        )


class AdminHospitalDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = (Role.ADMIN,)
    model = Hospital
    template_name = "dashboards/admin/hospital_detail.html"
    context_object_name = "hospital"

    def post(self, request, pk):
        hospital = get_object_or_404(Hospital, pk=pk)
        try:
            if request.POST.get("action") == "approve":
                approve_hospital(hospital, by=request.user)
                messages.success(request, f"{hospital.name} approved.")
            elif request.POST.get("action") == "reject":
                reject_hospital(hospital, by=request.user, reason=request.POST.get("reason", ""))
                messages.success(request, f"{hospital.name} rejected.")
        except DomainError as error:
            messages.error(request, str(error))
        return redirect("dashboards:admin-hospital-detail", pk=pk)


class AdminLicenceView(RoleRequiredMixin, View):
    """The only way to read a licence file: admin-only, never via MEDIA_URL."""

    allowed_roles = (Role.ADMIN,)

    def get(self, request, pk):
        hospital = get_object_or_404(Hospital, pk=pk)
        if not hospital.licence_proof:
            raise Http404
        return FileResponse(hospital.licence_proof.open("rb"), as_attachment=False)


class AdminUserListView(RoleRequiredMixin, ListView):
    allowed_roles = (Role.ADMIN,)
    template_name = "dashboards/admin/users.html"
    context_object_name = "users"
    paginate_by = 50

    def get_queryset(self):
        users = User.objects.order_by("role", "email")
        role = self.request.GET.get("role")
        if role in Role.values:
            users = users.filter(role=role)
        return users

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            roles=Role.choices, current=self.request.GET.get("role", ""), **kwargs
        )
