from decimal import Decimal, InvalidOperation
from pathlib import Path

from django import forms

from accounts.forms import NewAccountFieldsMixin
from core.forms import BootstrapFormMixin
from hospitals.models import Hospital

LICENCE_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
COORDINATE_STEP = Decimal("0.000001")


def validate_licence_file(upload) -> None:
    if Path(upload.name).suffix.lower() not in LICENCE_EXTENSIONS:
        raise forms.ValidationError("Upload a PDF, JPG or PNG file.")
    if upload.size > MAX_UPLOAD_BYTES:
        raise forms.ValidationError("File too large (max 5 MB).")


def parse_coordinate(text: str, limit: int) -> Decimal | None:
    """Parse a coordinate, round it to 6 decimal places (~10 cm) and check its range."""
    try:
        value = Decimal(text.strip())
        if not value.is_finite():
            return None
        value = value.quantize(COORDINATE_STEP)
    except (InvalidOperation, ValueError):
        return None
    return value if -limit <= value <= limit else None


def validate_photo_size(upload) -> None:
    if upload and upload.size > MAX_UPLOAD_BYTES:
        raise forms.ValidationError("File too large (max 5 MB).")


class HospitalRegistrationForm(BootstrapFormMixin, NewAccountFieldsMixin, forms.ModelForm):
    """Public sign-up form for hospitals. The view passes cleaned_data to register_hospital()."""

    # Text, not DecimalField: Google Maps copies ~15 decimals, often as one "lat, lng" string.
    latitude = forms.CharField(
        help_text="Right-click your hospital in Google Maps and click the coordinates to copy "
        "them. You can paste both numbers here.",
    )
    longitude = forms.CharField(required=False)
    licence_proof = forms.FileField(
        validators=[validate_licence_file], help_text="PDF, JPG or PNG, up to 5 MB."
    )
    photo = forms.ImageField(required=False, validators=[validate_photo_size])

    class Meta:
        model = Hospital
        fields = ["name", "place", "phone", "latitude", "longitude", "licence_proof", "photo"]

    def clean(self):
        cleaned = super().clean()
        lat_text = cleaned.get("latitude") or ""
        lng_text = cleaned.get("longitude") or ""
        if "," in lat_text and not lng_text.strip():
            lat_text, lng_text = lat_text.split(",", 1)
        for field, text, limit in (("latitude", lat_text, 90), ("longitude", lng_text, 180)):
            if field in self.errors:
                continue
            value = parse_coordinate(text, limit)
            if value is None:
                self.add_error(field, f"Enter a number between -{limit} and {limit}.")
            else:
                cleaned[field] = value
        return cleaned

    def _post_clean(self):
        # The Hospital has no user until register_hospital() creates both, so skip model
        # validation here; the fields above already carry every rule.
        pass
