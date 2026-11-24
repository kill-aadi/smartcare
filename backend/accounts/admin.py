from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "role", "is_active", "date_joined"]
    list_filter = ["role", "is_active"]
    search_fields = ["email"]
    fieldsets = [
        (None, {"fields": ["email", "password", "role"]}),
        ("Permissions", {"fields": ["is_active", "is_staff", "is_superuser", "groups"]}),
        ("Dates", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [
        (None, {"classes": ["wide"], "fields": ["email", "role", "password1", "password2"]})
    ]
