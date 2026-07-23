"""Registration, sign-in, and profile management.

One set of views serves all three roles. Previously each portal carried its own
copy of login and signup, none of which checked that the account actually held
the role the portal was for, so an evaluator could sign in through the buyer
page and vice versa. Here the role lives on the profile and
``accounts:post_login`` sends each user to the dashboard they belong in.
"""

import logging

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST

from events.decorators import get_profile, home_url_for
from events.forms import (
    AddressForm,
    EmailLoginForm,
    ProfileDetailsForm,
    SignUpForm,
    TopUpForm,
)
from events.models import CreditTransaction, Role
from events.services import credits
from events.throttle import (
    clear_attempts,
    client_ip,
    is_rate_limited,
    register_attempt,
)

logger = logging.getLogger("veritrade.accounts")

LOGIN_ATTEMPT_LIMIT = 8
LOGIN_ATTEMPT_WINDOW = 15 * 60  # seconds


class EmailLoginView(LoginView):
    """Sign in with an email address, rate limited per client address."""

    template_name = "accounts/login.html"
    form_class = EmailLoginForm
    redirect_authenticated_user = True

    def dispatch(self, request, *args, **kwargs):
        self.throttle_id = client_ip(request)
        if request.method == "POST" and is_rate_limited(
            "login", self.throttle_id,
            limit=LOGIN_ATTEMPT_LIMIT, window_seconds=LOGIN_ATTEMPT_WINDOW,
        ):
            messages.error(
                request, "Too many sign-in attempts. Try again in a few minutes."
            )
            return redirect("accounts:login")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        clear_attempts("login", self.throttle_id)
        logger.info("login success user=%s", form.get_user().pk)
        return super().form_valid(form)

    def form_invalid(self, form):
        register_attempt(
            "login", self.throttle_id, window_seconds=LOGIN_ATTEMPT_WINDOW
        )
        logger.warning("login failed ip=%s", self.throttle_id)
        return super().form_invalid(form)

    def get_success_url(self):
        return self.get_redirect_url() or reverse("accounts:post_login")

    def get_context_data(self, **kwargs):
        return super().get_context_data(page_title="Sign in", **kwargs)


@login_required
def post_login(request):
    """Send a freshly signed-in user to the dashboard for their role."""
    profile = get_profile(request.user)
    return redirect(home_url_for(profile.role))


def _signup(request, role, heading, blurb):
    """Shared registration flow, parameterised by the role being created."""
    if request.user.is_authenticated:
        return redirect("accounts:post_login")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(role=role)
            auth_login(
                request, user, backend="events.auth_backends.EmailBackend"
            )
            logger.info("signup user=%s role=%s", user.pk, role)
            messages.success(request, f"Welcome to VeriTrade, {user.first_name}.")
            return redirect("accounts:post_login")
    else:
        form = SignUpForm()

    return render(
        request,
        "accounts/signup.html",
        {
            "form": form,
            "role": role,
            "page_title": heading,
            "heading": heading,
            "blurb": blurb,
        },
    )


def signup_member(request):
    return _signup(
        request,
        Role.MEMBER,
        "Create your account",
        "Buy verified second-hand electronics, or sell the ones you no longer need.",
    )


def signup_evaluator(request):
    return _signup(
        request,
        Role.EVALUATOR,
        "Join as an evaluator",
        "Assess incoming devices and decide what makes it onto the marketplace.",
    )


def signup_courier(request):
    return _signup(
        request,
        Role.COURIER,
        "Join as a delivery partner",
        "Collect items from sellers and deliver them to buyers.",
    )


@require_POST
def logout_view(request):
    """Sign out. POST-only, so a stray link or prefetch cannot log you out."""
    auth_logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("marketing:index")


@login_required
def profile(request):
    """The signed-in user's own profile. There is no way to view another's."""
    profile_obj = get_profile(request.user)
    return render(
        request,
        "accounts/profile.html",
        {
            "profile": profile_obj,
            "page_title": "Your profile",
            "details_form": ProfileDetailsForm(instance=profile_obj),
            "address_form": AddressForm(instance=profile_obj),
            "password_form": PasswordChangeForm(request.user),
        },
    )


@login_required
@require_POST
def update_details(request):
    profile_obj = get_profile(request.user)
    form = ProfileDetailsForm(request.POST, request.FILES, instance=profile_obj)
    if form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:profile")

    return render(
        request,
        "accounts/profile.html",
        {
            "profile": profile_obj,
            "page_title": "Your profile",
            "details_form": form,
            "address_form": AddressForm(instance=profile_obj),
            "password_form": PasswordChangeForm(request.user),
        },
        status=400,
    )


@login_required
@require_POST
def update_address(request):
    profile_obj = get_profile(request.user)
    form = AddressForm(request.POST, instance=profile_obj)
    if form.is_valid():
        form.save()
        messages.success(request, "Address updated.")
        return redirect("accounts:profile")

    return render(
        request,
        "accounts/profile.html",
        {
            "profile": profile_obj,
            "page_title": "Your profile",
            "details_form": ProfileDetailsForm(instance=profile_obj),
            "address_form": form,
            "password_form": PasswordChangeForm(request.user),
        },
        status=400,
    )


@login_required
@require_POST
def change_password(request):
    """Change the password.

    Uses Django's ``PasswordChangeForm``, which requires the old password and
    runs every configured validator. The previous implementation checked
    neither strength nor confirmation properly and returned JSON that the page
    ignored.
    """
    profile_obj = get_profile(request.user)
    form = PasswordChangeForm(request.user, request.POST)
    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)  # Stay signed in.
        logger.info("password changed user=%s", user.pk)
        messages.success(request, "Password changed.")
        return redirect("accounts:profile")

    return render(
        request,
        "accounts/profile.html",
        {
            "profile": profile_obj,
            "page_title": "Your profile",
            "details_form": ProfileDetailsForm(instance=profile_obj),
            "address_form": AddressForm(instance=profile_obj),
            "password_form": form,
        },
        status=400,
    )


@login_required
@require_POST
def delete_account(request):
    """Permanently delete the account, after re-confirming the password."""
    password = request.POST.get("password", "")
    if not request.user.check_password(password):
        messages.error(request, "That password is not correct; nothing was deleted.")
        return redirect("accounts:profile")

    user_id = request.user.pk
    user = request.user
    auth_logout(request)
    user.delete()
    logger.info("account deleted user=%s", user_id)
    messages.success(request, "Your account has been deleted.")
    return redirect("marketing:index")


@login_required
def wallet(request):
    """Credit balance, top-up form, and the account's ledger history."""
    profile_obj = get_profile(request.user)
    form = TopUpForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            try:
                credits.top_up(request.user, form.cleaned_data["amount"])
            except ValueError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(
                    request, f"{form.cleaned_data['amount']} credits added."
                )
                return redirect("accounts:wallet")

    history = (
        CreditTransaction.objects.filter(account__user=request.user)
        .select_related("order")
        .order_by("-created_at")[:50]
    )

    return render(
        request,
        "accounts/wallet.html",
        {
            "profile": profile_obj,
            "page_title": "Credits",
            "form": form,
            "balance": credits.get_balance(request.user),
            "history": history,
        },
    )


login_view = EmailLoginView.as_view()
login_url = reverse_lazy("accounts:login")
