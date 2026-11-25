import posixpath

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import Http404
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

from hospitals.views import HospitalRegisterView

PRIVATE_MEDIA_DIRS = {"licences"}


def serve_public_media(request, path):
    """Dev-only media serving that refuses private folders (licences are admin-only)."""
    # Normalise first so "./licences/x" or "a/../licences/x" can't sneak past the check.
    path = posixpath.normpath(path).lstrip("/")
    if not settings.DEBUG or path.split("/", 1)[0] in PRIVATE_MEDIA_DIRS:
        raise Http404
    return serve(request, path, document_root=settings.MEDIA_ROOT)


urlpatterns = [
    path("", RedirectView.as_view(pattern_name="dashboards:root"), name="home"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/hospital/", HospitalRegisterView.as_view(), name="hospital-register"),
    path("dashboard/", include("dashboards.urls")),
    path("django-admin/", admin.site.urls),
    path("api/", include("config.api_urls")),
    path("api/schema/", SpectacularAPIView.as_view(permission_classes=[AllowAny]), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[AllowAny]),
        name="api-docs",
    ),
    # Uploaded photos in development. Production (v2) serves media from Blob Storage instead.
    re_path(r"^media/(?P<path>.*)$", serve_public_media),
]
