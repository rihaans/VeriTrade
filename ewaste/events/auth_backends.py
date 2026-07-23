"""Email-based authentication.

The login forms ask for an email address. The previous implementation did
``User.objects.get(email=...)`` in the view, which raised
``MultipleObjectsReturned`` (a 500) as soon as two accounts shared an address,
and leaked account existence by answering "Email not registered" before any
password was checked.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class EmailBackend(ModelBackend):
    """Authenticate with an email address instead of a username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get("email") or username
        if not email or not password:
            return None

        # iexact, because email addresses are not case-sensitive in practice.
        # first() rather than get(): a duplicate must not become a 500.
        user = UserModel.objects.filter(email__iexact=email.strip()).order_by("pk").first()

        if user is None:
            # Run the hasher anyway so a missing account and a wrong password
            # take the same amount of time. Without this, response timing
            # enumerates registered addresses.
            UserModel().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
