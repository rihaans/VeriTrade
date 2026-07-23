from django.apps import AppConfig


class EventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "events"
    verbose_name = "Marketplace core"

    def ready(self):
        # Registers the post_save hook that gives every user a profile and a
        # credit account. Imported here so the app registry is fully loaded.
        from . import signals  # noqa: F401
