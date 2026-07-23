"""Credit movements.

Two rules, enforced here and nowhere else:

1. A balance is only ever changed together with a :class:`CreditTransaction`
   row describing why. Reading the ledger for an account and summing ``amount``
   must always equal ``CreditAccount.balance``; :func:`reconcile` asserts it.
2. Every change happens under a row lock inside a transaction. The old code did
   ``account.Credits -= price; account.save()``, which loses writes whenever two
   requests overlap and lets the balance go negative.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.db.models import Sum

from ..models import CreditAccount, CreditTransaction

logger = logging.getLogger("veritrade.credits")


class InsufficientCredits(Exception):
    """Raised when an account cannot cover a debit."""

    def __init__(self, required, available):
        self.required = required
        self.available = available
        super().__init__(
            f"Needs {required} credits but only {available} available."
        )


def _locked_account(user):
    """Fetch the account for update, creating it if it somehow does not exist.

    ``select_for_update`` is a no-op on SQLite, which is why the SQLite
    configuration opens write transactions in IMMEDIATE mode; that takes the
    database write lock up front and serialises concurrent checkouts.
    """
    account, _ = CreditAccount.objects.get_or_create(user=user)
    return CreditAccount.objects.select_for_update().get(pk=account.pk)


def get_balance(user):
    account = CreditAccount.objects.filter(user=user).only("balance").first()
    return account.balance if account else 0


def deposit(user, amount, *, kind, memo="", order=None):
    """Add ``amount`` credits to ``user``. Must run inside an atomic block."""
    if amount <= 0:
        raise ValueError("Deposit amount must be positive.")

    account = _locked_account(user)
    account.balance += amount
    account.save(update_fields=["balance", "updated_at"])

    entry = CreditTransaction.objects.create(
        account=account,
        kind=kind,
        amount=amount,
        balance_after=account.balance,
        order=order,
        memo=memo,
    )
    logger.info(
        "credit deposit user=%s amount=%s kind=%s balance=%s",
        user.pk, amount, kind, account.balance,
    )
    return entry


def withdraw(user, amount, *, kind, memo="", order=None):
    """Remove ``amount`` credits from ``user``. Must run inside an atomic block.

    Raises :class:`InsufficientCredits` rather than allowing a negative balance.
    """
    if amount <= 0:
        raise ValueError("Withdrawal amount must be positive.")

    account = _locked_account(user)
    if account.balance < amount:
        raise InsufficientCredits(required=amount, available=account.balance)

    account.balance -= amount
    account.save(update_fields=["balance", "updated_at"])

    entry = CreditTransaction.objects.create(
        account=account,
        kind=kind,
        amount=-amount,
        balance_after=account.balance,
        order=order,
        memo=memo,
    )
    logger.info(
        "credit withdrawal user=%s amount=%s kind=%s balance=%s",
        user.pk, amount, kind, account.balance,
    )
    return entry


@transaction.atomic
def top_up(user, amount):
    """Mock top-up: grants credits with no payment provider behind it.

    This exists so the marketplace is usable as a demo. It is capped by
    ``MAX_TOPUP_CREDITS`` so a mistyped amount cannot mint an unusable fortune,
    and it is the only place in the codebase that creates credits from nothing.
    Wiring a real payment provider means replacing this function's body with a
    charge confirmation and leaving every caller untouched.
    """
    if amount <= 0:
        raise ValueError("Top-up amount must be positive.")
    if amount > settings.MAX_TOPUP_CREDITS:
        raise ValueError(
            f"The maximum single top-up is {settings.MAX_TOPUP_CREDITS} credits."
        )

    return deposit(
        user,
        amount,
        kind=CreditTransaction.Kind.TOPUP,
        memo="Demo top-up (no payment taken)",
    )


def reconcile(user):
    """Return (balance, ledger_sum) so the two can be compared.

    Used by the test suite and the ``check_ledger`` management command; a
    mismatch means a balance was written without a matching ledger row.
    """
    account = CreditAccount.objects.filter(user=user).first()
    if account is None:
        return 0, 0
    ledger_sum = account.transactions.aggregate(total=Sum("amount"))["total"] or 0
    return account.balance, ledger_sum
