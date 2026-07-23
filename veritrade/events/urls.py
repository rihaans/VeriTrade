"""Public routes under the ``marketing`` namespace."""

from django.urls import path

from . import views

app_name = "marketing"

urlpatterns = [
    path("", views.index, name="index"),
    path("how-it-works/", views.how_it_works, name="how_it_works"),
]
