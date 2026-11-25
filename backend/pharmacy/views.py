"""Hospital dashboard pages for managing the hospital's own pharmacies."""

from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import FormView, ListView

from dashboards.mixins import ApprovedHospitalRequiredMixin
from pharmacy.forms import PharmacyCreateForm
from pharmacy.services import create_pharmacy


class HospitalPharmacyListView(ApprovedHospitalRequiredMixin, ListView):
    template_name = "dashboards/hospital/pharmacies.html"
    context_object_name = "pharmacies"

    def get_queryset(self):
        return self.hospital.pharmacies.all()


class HospitalPharmacyCreateView(ApprovedHospitalRequiredMixin, FormView):
    template_name = "dashboards/hospital/pharmacy_form.html"
    form_class = PharmacyCreateForm

    def form_valid(self, form):
        data = form.cleaned_data
        pharmacy = create_pharmacy(
            self.hospital,
            email=data["email"],
            password=data["password1"],
            name=data["name"],
            phone=data["phone"],
        )
        messages.success(self.request, f"{pharmacy.name} added.")
        return redirect("dashboards:hospital-pharmacies")
