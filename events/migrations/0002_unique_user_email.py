"""Enforce one account per email address at the database level.

The application authenticates by email, but ``django.contrib.auth.User.email``
carries no unique constraint, so nothing stopped two accounts from claiming the
same address. Form validation alone cannot close the race between two
simultaneous signups; this index can.

The index is partial so that accounts with no email address (``createsuperuser``
permits this) do not all collide on the empty string. Partial indexes are
supported by both SQLite and PostgreSQL.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique_ci "
                "ON auth_user (LOWER(email)) WHERE email != '';"
            ),
            reverse_sql="DROP INDEX IF EXISTS auth_user_email_unique_ci;",
        ),
    ]
