"""Credit accounting: balances, the ledger, and the rules protecting both."""

from django.conf import settings
from django.test import TestCase

from events.models import CreditTransaction
from events.services import credits

from .factories import make_user


class DepositWithdrawTests(TestCase):
    def setUp(self):
        self.profile = make_user()
        self.user = self.profile.user

    def test_new_account_starts_empty(self):
        self.assertEqual(credits.get_balance(self.user), 0)

    def test_deposit_increases_balance_and_writes_ledger_entry(self):
        credits.deposit(
            self.user, 500, kind=CreditTransaction.Kind.TOPUP, memo="test"
        )

        self.assertEqual(credits.get_balance(self.user), 500)
        entry = CreditTransaction.objects.get()
        self.assertEqual(entry.amount, 500)
        self.assertEqual(entry.balance_after, 500)

    def test_withdraw_records_a_negative_amount(self):
        credits.deposit(self.user, 500, kind=CreditTransaction.Kind.TOPUP)
        credits.withdraw(self.user, 200, kind=CreditTransaction.Kind.PURCHASE)

        self.assertEqual(credits.get_balance(self.user), 300)
        entry = CreditTransaction.objects.latest("created_at")
        self.assertEqual(entry.amount, -200)
        self.assertEqual(entry.balance_after, 300)

    def test_withdraw_beyond_balance_is_refused(self):
        credits.deposit(self.user, 100, kind=CreditTransaction.Kind.TOPUP)

        with self.assertRaises(credits.InsufficientCredits):
            credits.withdraw(self.user, 101, kind=CreditTransaction.Kind.PURCHASE)

        # The failed attempt must leave nothing behind.
        self.assertEqual(credits.get_balance(self.user), 100)
        self.assertEqual(CreditTransaction.objects.count(), 1)

    def test_non_positive_amounts_are_rejected(self):
        for amount in (0, -5):
            with self.assertRaises(ValueError):
                credits.deposit(self.user, amount, kind=CreditTransaction.Kind.TOPUP)
            with self.assertRaises(ValueError):
                credits.withdraw(self.user, amount, kind=CreditTransaction.Kind.PURCHASE)

    def test_balance_always_equals_the_sum_of_the_ledger(self):
        credits.deposit(self.user, 900, kind=CreditTransaction.Kind.TOPUP)
        credits.withdraw(self.user, 350, kind=CreditTransaction.Kind.PURCHASE)
        credits.deposit(self.user, 120, kind=CreditTransaction.Kind.REFUND)

        balance, ledger_sum = credits.reconcile(self.user)
        self.assertEqual(balance, ledger_sum)
        self.assertEqual(balance, 670)


class TopUpTests(TestCase):
    def setUp(self):
        self.profile = make_user()

    def test_top_up_is_capped(self):
        with self.assertRaises(ValueError):
            credits.top_up(self.profile.user, settings.MAX_TOPUP_CREDITS + 1)

    def test_top_up_at_the_cap_is_allowed(self):
        credits.top_up(self.profile.user, settings.MAX_TOPUP_CREDITS)
        self.assertEqual(
            credits.get_balance(self.profile.user), settings.MAX_TOPUP_CREDITS
        )

    def test_negative_top_up_is_rejected(self):
        with self.assertRaises(ValueError):
            credits.top_up(self.profile.user, -100)
