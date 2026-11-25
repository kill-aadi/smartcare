from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect

from accounts.models import Role
from hospitals.models import ApprovalStatus


class RoleRequiredMixin(AccessMixin):
    """Anonymous users go to the login page; logged-in users with the wrong role get 403."""

    allowed_roles: tuple[str, ...] = ()
    raise_exception = False

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in self.allowed_roles:
            self.raise_exception = True  # logged in but not allowed: 403, not a login loop
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class ApprovedHospitalRequiredMixin(RoleRequiredMixin):
    """Hospital pages that need an approved hospital; pending/rejected ones see a status page."""

    allowed_roles = (Role.HOSPITAL,)

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated and user.role == Role.HOSPITAL:
            status = user.hospital.approval_status
            if status == ApprovalStatus.PENDING:
                return redirect("dashboards:pending")
            if status == ApprovalStatus.REJECTED:
                return redirect("dashboards:rejected")
            self.hospital = user.hospital
        return super().dispatch(request, *args, **kwargs)
