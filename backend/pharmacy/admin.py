from django.contrib import admin

from pharmacy.models import Pharmacy


@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = ["name", "hospital", "phone"]
    search_fields = ["name"]
