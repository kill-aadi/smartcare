from pathlib import Path

from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator

from accounts.forms import NewAccountFieldsMixin
from core.forms import BootstrapFormMixin
from hospitals.models import Hospital

LICENCE_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def validate_licence_file(upload) -> None:
    if Path(upload.name).suffix.lower() not in LICENCE_EXTENSIONS:
        raise forms.ValidationError("Upload a PDF, JPG or PNG file.")
    if upload.size > MAX_UPLOAD_BYTES:
        raise forms.ValidationError("File too large (max 5 MB).")


def validate_photo_size(upload) -> None:
    if upload and upload.size > MAX_UPLOAD_BYTES:
        raise forms.ValidationError("File too large (max 5 MB).")


class HospitalRegistrationForm(BootstrapFormMixin, NewAccountFieldsMixin, forms.ModelForm):
    """Public sign-up form for hospitals. The view passes cleaned_data to register_hospital()."""

    latitude = forms.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text="Right-click your hospital in Google Maps to copy its coordinates.",
    )
    longitude = forms.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    licence_proof = forms.FileField(
        validators=[validate_licence_file], help_text="PDF, JPG or PNG, up to 5 MB."
    )
    photo = forms.ImageField(required=False, validators=[validate_photo_size])

    class Meta:
        model = Hospital
        fields = ["name", "place", "phone", "latitude", "longitude", "licence_proof", "photo"]

    def _post_clean(self):
        # The Hospital has no user until register_hospital() creates both, so skip model
        # validation here; the fields above already carry every rule.
        pass
