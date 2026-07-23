"""Root URL configuration.

Namespaces:
    marketing    public pages
    accounts     registration, sign-in, profile, credits
    marketplace  buying and selling
    evaluation   evaluator workspace
    logistics    courier workspace

The old single-page-per-role login URLs are kept as permanent redirects so
existing links and bookmarks continue to resolve after the move to unified,
role-aware authentication.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", include("events.urls")),
    path("accounts/", include("base.urls_accounts")),
    path("market/", include("base.urls")),
    path("evaluation/", include("eval.urls")),
    path("logistics/", include("delivery.urls")),
    path("admin/", admin.site.urls),

    # Legacy routes.
    path("login/", RedirectView.as_view(pattern_name="accounts:login", permanent=True)),
    path("signup/", RedirectView.as_view(pattern_name="accounts:signup", permanent=True)),
    path(
        "eval/login",
        RedirectView.as_view(pattern_name="accounts:login", permanent=True),
    ),
    path(
        "eval/signup",
        RedirectView.as_view(pattern_name="accounts:signup_evaluator", permanent=True),
    ),
    path(
        "dlv/login",
        RedirectView.as_view(pattern_name="accounts:login", permanent=True),
    ),
    path(
        "dlv/signup",
        RedirectView.as_view(pattern_name="accounts:signup_courier", permanent=True),
    ),
]

if settings.DEBUG:
    # In production the media root is served by the web server or object store,
    # never by Django. Serving it here unconditionally, as the old config did,
    # hands out every uploaded file through the application process.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
