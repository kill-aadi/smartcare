"""Business-rule errors raised by service modules.

Services raise these instead of HTTP errors, so one rule serves the web dashboards (shown as a
message) and the API (turned into JSON by ``core.api.domain_exception_handler``).
"""


class DomainError(Exception):
    """A broken business rule. ``code`` is machine-readable; ``status`` is the API HTTP status."""

    code: str = "domain_error"
    status: int = 400


class NotAllowed(DomainError):
    code = "not_allowed"
    status = 403


class InvalidTransition(DomainError):
    code = "invalid_transition"
    status = 400


class AlreadyPaid(DomainError):
    code = "already_paid"
    status = 409
