"""Migrate the extra (non tenant-aware) databases.

django-tenants replaces ``migrate`` with ``migrate_schemas``, which only knows
about the tenant database. Databases declared in ``DATABASE_EXTRA_URLS`` use
Django's stock migrate command instead; this wrapper runs it for each of them.

    python manage.py migrate_extra               # every extra database
    python manage.py migrate_extra analytics     # just one
"""

from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.core.management.commands.migrate import Command as DjangoMigrateCommand
from django.db import connections


class Command(BaseCommand):
    help = "Run Django's migrate on the extra (non tenant-aware) databases."

    def add_arguments(self, parser):
        parser.add_argument("aliases", nargs="*", help="Database aliases (default: all extras).")

    def extra_aliases(self) -> list[str]:
        tenant_aware = {"default", *settings.DATABASE_REPLICAS}
        return [alias for alias in connections if alias not in tenant_aware]

    def handle(self, *args, aliases, verbosity, **options):
        available = self.extra_aliases()
        unknown = set(aliases) - set(available)
        if unknown:
            raise CommandError(f"Not extra databases: {', '.join(sorted(unknown))}")
        targets = aliases or available
        if not targets:
            self.stdout.write("No extra databases configured (DATABASE_EXTRA_URLS is empty).")
            return
        for alias in targets:
            self.stdout.write(self.style.MIGRATE_HEADING(f"Migrating extra database {alias!r}"))
            cmd = DjangoMigrateCommand(stdout=self.stdout, stderr=self.stderr)
            cmd.run_from_argv(["manage.py", "migrate", "--database", alias, f"-v{verbosity}"])
