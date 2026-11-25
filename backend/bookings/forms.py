from django import forms

from core.forms import BootstrapFormMixin


class SessionForm(BootstrapFormMixin, forms.Form):
    """Doctor's "add a session" form. The view hands cleaned_data to create_session()."""

    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    end_time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    fee = forms.DecimalField(min_value=0, max_digits=8, decimal_places=2, label="Fee (₹)")
    capacity = forms.IntegerField(min_value=1, max_value=200, help_text="Most patients you'll see.")
    avg_consult_minutes = forms.IntegerField(
        min_value=1,
        max_value=120,
        initial=10,
        label="Average minutes per patient",
        help_text="Used for the waiting-time estimate patients see.",
    )

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_time"), cleaned.get("end_time")
        if start and end and end <= start:
            self.add_error("end_time", "End time must be after the start time.")
        return cleaned
