"""Hospital dashboard pages for managing the hospital's own doctors."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import FormView, ListView, UpdateView

from dashboards.mixins import ApprovedHospitalRequiredMixin
from doctors.forms import DoctorCreateForm, DoctorEditForm
from doctors.services import create_doctor, set_doctor_active


class HospitalDoctorListView(ApprovedHospitalRequiredMixin, ListView):
    template_name = "dashboards/hospital/doctors.html"
    context_object_name = "doctors"

    def get_queryset(self):
        return self.hospital.doctors.select_related("specialization", "user")


class HospitalDoctorCreateView(ApprovedHospitalRequiredMixin, FormView):
    template_name = "dashboards/hospital/doctor_form.html"
    form_class = DoctorCreateForm

    def form_valid(self, form):
        data = form.cleaned_data
        doctor = create_doctor(
            self.hospital,
            email=data["email"],
            password=data["password1"],
            name=data["name"],
            specialization=data["specialization"],
            qualification=data["qualification"],
            experience_years=data["experience_years"],
            gender=data["gender"],
            photo=data.get("photo"),
        )
        messages.success(
            self.request, f"{doctor.name} added. They can log in with {data['email']}."
        )
        return redirect("dashboards:hospital-doctors")


class HospitalDoctorUpdateView(ApprovedHospitalRequiredMixin, UpdateView):
    template_name = "dashboards/hospital/doctor_form.html"
    form_class = DoctorEditForm
    context_object_name = "doctor"

    def get_queryset(self):
        return self.hospital.doctors.all()  # another hospital's doctor -> 404

    def form_valid(self, form):
        messages.success(self.request, "Doctor updated.")
        form.save()
        return redirect("dashboards:hospital-doctors")


class HospitalDoctorToggleActiveView(ApprovedHospitalRequiredMixin, View):
    def post(self, request, pk):
        doctor = get_object_or_404(self.hospital.doctors.select_related("user"), pk=pk)
        set_doctor_active(self.hospital, doctor, not doctor.user.is_active)
        state = "reactivated" if doctor.user.is_active else "deactivated"
        messages.success(request, f"{doctor.name} {state}.")
        return redirect("dashboards:hospital-doctors")
