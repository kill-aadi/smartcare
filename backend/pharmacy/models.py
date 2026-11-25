from django.conf import settings
from django.db import models


class Pharmacy(models.Model):
    """A pharmacy at one hospital; patients forward their prescriptions to it."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pharmacy"
    )
    hospital = models.ForeignKey(
        "hospitals.Hospital", on_delete=models.CASCADE, related_name="pharmacies"
    )
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    email = models.EmailField()

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "pharmacies"

    def __str__(self):
        return self.name
