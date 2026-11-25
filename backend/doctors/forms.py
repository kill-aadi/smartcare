from django import forms

from accounts.forms import NewAccountFieldsMixin
from core.forms import BootstrapFormMixin
from doctors.models import Doctor
from hospitals.forms import validate_photo_size

DOCTOR_FIELDS = ["name", "specialization", "qualification", "experience_years", "gender", "photo"]


class DoctorEditForm(BootstrapFormMixin, forms.ModelForm):
    photo = forms.ImageField(required=False, validators=[validate_photo_size])

    class Meta:
        model = Doctor
        fields = DOCTOR_FIELDS


class DoctorCreateForm(NewAccountFieldsMixin, DoctorEditForm):
    """Adds the doctor's login. The view hands cleaned_data to create_doctor()."""

    def _post_clean(self):
        # No user or hospital yet: create_doctor() sets both, so skip model validation here.
        pass
