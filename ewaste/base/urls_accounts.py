"""Account routes, mounted at /accounts/ under the ``accounts`` namespace."""

from django.urls import path

from .views import accounts

app_name = "accounts"

urlpatterns = [
    path("login/", accounts.login_view, name="login"),
    path("logout/", accounts.logout_view, name="logout"),
    path("post-login/", accounts.post_login, name="post_login"),

    path("signup/", accounts.signup_member, name="signup"),
    path("signup/evaluator/", accounts.signup_evaluator, name="signup_evaluator"),
    path("signup/courier/", accounts.signup_courier, name="signup_courier"),

    path("profile/", accounts.profile, name="profile"),
    path("profile/details/", accounts.update_details, name="update_details"),
    path("profile/address/", accounts.update_address, name="update_address"),
    path("profile/password/", accounts.change_password, name="change_password"),
    path("profile/delete/", accounts.delete_account, name="delete_account"),

    path("credits/", accounts.wallet, name="wallet"),
]
