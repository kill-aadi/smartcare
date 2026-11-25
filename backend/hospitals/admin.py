from django.contrib import admin

from hospitals.models import Hospital


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ["name", "place", "approval_status", "created_at"]
    list_filter = ["approval_status"]
    search_fields = ["name", "place", "email"]
