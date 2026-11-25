from django import forms

from accounts.forms import NewAccountFieldsMixin
from core.forms import BootstrapFormMixin
from pharmacy.models import Pharmacy


class PharmacyCreateForm(BootstrapFormMixin, NewAccountFieldsMixin, forms.ModelForm):
    class Meta:
        model = Pharmacy
        fields = ["name", "phone"]

    def _post_clean(self):
        # create_pharmacy() sets user, hospital and email.
        pass
