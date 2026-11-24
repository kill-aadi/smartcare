from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Authenticate by email, ignoring case."""

    def authenticate(self, request, email=None, password=None, username=None, **kwargs):
        email = email or username  # Django's login form posts the USERNAME_FIELD as "username"
        if not email or password is None:
            return None
        try:
            user = get_user_model().objects.get(email__iexact=email.strip())
        except get_user_model().DoesNotExist:
            get_user_model()().set_password(password)  # same work as a real check: no timing leak
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
