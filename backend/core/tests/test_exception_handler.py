from rest_framework.permissions import AllowAny
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from core.exceptions import DomainError, NotAllowed


class Conflict(DomainError):
    code = "conflict"
    status = 409


class _Boom(APIView):
    permission_classes = [AllowAny]
    error: Exception | None = None

    def get(self, request):
        raise self.error


def _call(error):
    view = _Boom.as_view(error=error)
    return view(APIRequestFactory().get("/"))


def test_domain_error_becomes_json_with_its_status_and_code():
    response = _call(Conflict("nope"))

    assert response.status_code == 409
    assert response.data == {"detail": "nope", "code": "conflict"}


def test_shared_not_allowed_is_403():
    response = _call(NotAllowed("not yours"))

    assert response.status_code == 403
    assert response.data == {"detail": "not yours", "code": "not_allowed"}
