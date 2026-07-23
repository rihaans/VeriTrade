"""Courier routes, mounted at /logistics/ under the ``logistics`` namespace."""

from django.urls import path

from . import views

app_name = "logistics"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("queue/", views.queue, name="queue"),
    path("queue/<int:pk>/claim/", views.claim, name="claim"),
    path("current/", views.current, name="current"),
    path("current/pick-up/", views.pick_up, name="pick_up"),
    path("current/deliver/", views.deliver, name="deliver"),
    path("history/", views.history, name="history"),
]
