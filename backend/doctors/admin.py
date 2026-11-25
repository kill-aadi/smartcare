from django.contrib import admin

from doctors.models import Doctor, Specialization


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ["name", "specialization", "hospital"]
    list_filter = ["specialization"]
    search_fields = ["name"]
