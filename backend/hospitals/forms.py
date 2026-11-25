from pathlib import Path

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.validators import MaxValueValidator, MinValueValidator

from accounts.models import DUPLICATE_EMAIL_MESSAGE, User
from hospitals.models import Hospital

LICENCE_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def validate_licence_file(upload) -> None:
    if Path(upload.name).suffix.lower() not in LICENCE_EXTENSIONS:
        raise forms.ValidationError("Upload a PDF, JPG or PNG file.")
    if upload.size > MAX_UPLOAD_BYTES:
        raise forms.ValidationError("File too large (max 5 MB).")


class HospitalRegistrationForm(forms.ModelForm):
    """Public sign-up form for hospitals. The view passes cleaned_data to register_hospital()."""

    email = forms.EmailField(help_text="You'll use this to log in.")
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)
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
    photo = forms.ImageField(required=False)

    class Meta:
        model = Hospital
        fields = ["name", "place", "phone", "latitude", "longitude", "licence_proof", "photo"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(DUPLICATE_EMAIL_MESSAGE)
        return email

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and photo.size > MAX_UPLOAD_BYTES:
            raise forms.ValidationError("File too large (max 5 MB).")
        return photo

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "The two passwords don't match.")
        elif p2:
            try:
                validate_password(p2, User(email=cleaned.get("email", "")))
            except forms.ValidationError as error:
                self.add_error("password2", error)
        return cleaned

    def _post_clean(self):
        # The Hospital instance has no user yet; register_hospital() creates both. Skip model
        # validation here so the missing user doesn't produce a confusing error.
        pass
