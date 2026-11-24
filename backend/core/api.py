from rest_framework.response import Response
from rest_framework.views import exception_handler

from core.exceptions import DomainError


def domain_exception_handler(exc, context):
    """Turn a ``DomainError`` into ``{"detail", "code"}`` JSON; defer the rest to DRF."""
    if isinstance(exc, DomainError):
        return Response({"detail": str(exc), "code": exc.code}, status=exc.status)
    return exception_handler(exc, context)
