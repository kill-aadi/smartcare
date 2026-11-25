from django import forms
from django.contrib.auth.password_validation import validate_password

from accounts.models import DUPLICATE_EMAIL_MESSAGE, User


class NewAccountFieldsMixin(forms.Form):
    """Email + password fields for forms that create a login (hospital, doctor, pharmacy).

    The view passes ``cleaned_data["email"]`` and ``cleaned_data["password1"]`` to a service.
    """

    email = forms.EmailField(help_text="Used to log in.")
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(DUPLICATE_EMAIL_MESSAGE)
        return email

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
