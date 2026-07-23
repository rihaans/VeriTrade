"""Access control decorators.

The old code identified the acting user from an ``<int:pk>`` in the URL and
never compared it to the session, so ``/direct_buy/7/12/`` spent user 7's
credits regardless of who sent the request. Views no longer take a user id at
all: the actor is always ``request.user``, and these decorators establish that
the actor holds the right role before the view body runs.
"""

import functools

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

from .models import Role, UserProfile


def get_profile(user):
    """Return the user's profile, creating it if a legacy account lacks one."""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def role_required(*roles):
    """Allow only signed-in users whose profile carries one of ``roles``.

    Staff bypass the role check so an administrator can inspect any dashboard.
    A signed-in user with the wrong role is sent to their own home rather than
    shown a 403, because the usual cause is a stale bookmark.
    """

    def decorator(view):
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(
                    request.get_full_path(), settings.LOGIN_URL
                )

            profile = get_profile(request.user)
            if profile.role in roles or request.user.is_staff:
                request.profile = profile
                return view(request, *args, **kwargs)

            messages.warning(
                request, "That area is not available for your account type."
            )
            return redirect(home_url_for(profile.role))

        return wrapper

    return decorator


member_required = role_required(Role.MEMBER)
evaluator_required = role_required(Role.EVALUATOR)
courier_required = role_required(Role.COURIER)


def home_url_for(role):
    """The landing route for a given role, used after login and on redirect."""
    return {
        Role.MEMBER: "marketplace:home",
        Role.EVALUATOR: "evaluation:dashboard",
        Role.COURIER: "logistics:dashboard",
    }.get(role, "marketplace:home")
