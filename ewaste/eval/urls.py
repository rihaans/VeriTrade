"""Evaluator routes, mounted at /evaluation/ under the ``evaluation`` namespace."""

from django.urls import path

from . import views

app_name = "evaluation"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("queue/", views.queue, name="queue"),
    path("queue/<int:pk>/claim/", views.claim, name="claim"),
    path("current/", views.current, name="current"),
    path("current/submit/", views.submit, name="submit"),
    path("current/release/", views.release, name="release"),
    path("history/", views.history, name="history"),
]
