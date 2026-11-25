from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import FormView

from hospitals.forms import HospitalRegistrationForm
from hospitals.services import register_hospital


class HospitalRegisterView(FormView):
    template_name = "hospitals/register.html"
    form_class = HospitalRegistrationForm

    def form_valid(self, form):
        data = form.cleaned_data
        register_hospital(
            email=data["email"],
            password=data["password1"],
            name=data["name"],
            place=data["place"],
            phone=data["phone"],
            latitude=data["latitude"],
            longitude=data["longitude"],
            licence_proof=data["licence_proof"],
            photo=data.get("photo"),
        )
        messages.success(self.request, "Thanks — an admin will review your registration.")
        return redirect("login")
