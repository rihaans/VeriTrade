"""Reconcile every credit balance against its ledger.

    python manage.py check_ledger

Exits non-zero if any account's ``balance`` disagrees with the sum of its
transactions, which would mean a balance was written somewhere other than
``events.services.credits``. Safe to run against production on a schedule.
"""

from django.core.management.base import BaseCommand
from django.db.models import Sum

from events.models import CreditAccount


class Command(BaseCommand):
    help = "Verify that every credit balance matches its transaction history."

    def handle(self, *args, **options):
        accounts = CreditAccount.objects.select_related("user").annotate(
            ledger_total=Sum("transactions__amount")
        )

        discrepancies = []
        for account in accounts:
            ledger_total = account.ledger_total or 0
            if account.balance != ledger_total:
                discrepancies.append((account, ledger_total))

        checked = len(accounts)
        if not discrepancies:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{checked} account(s) checked, all balances reconcile."
                )
            )
            return

        for account, ledger_total in discrepancies:
            self.stderr.write(
                self.style.ERROR(
                    f"{account.user.get_username()}: balance={account.balance} "
                    f"ledger={ledger_total} drift={account.balance - ledger_total}"
                )
            )

        raise SystemExit(
            f"{len(discrepancies)} of {checked} account(s) failed reconciliation."
        )
