"""Guarantee that every user has a profile and a credit account.

Users are created from several places: the signup views, ``createsuperuser``,
the admin, and test fixtures. Rather than repeat the setup at each call site
(and crash in a view when one is forgotten), it hangs off ``post_save``.
"""

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CreditAccount, UserProfile


@receiver(post_save, sender=User, dispatch_uid="events.bootstrap_user_records")
def bootstrap_user_records(sender, instance, created, **kwargs):
    if not created:
        return
    # get_or_create keeps this safe if a caller has already made them, which is
    # what the registration service does when it needs to set a non-default role.
    UserProfile.objects.get_or_create(user=instance)
    CreditAccount.objects.get_or_create(user=instance)
