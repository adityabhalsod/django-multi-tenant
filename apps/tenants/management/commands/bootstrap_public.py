from django.conf import settings
from django.core.management.base import BaseCommand

from apps.tenants.services import ensure_public_tenant


class Command(BaseCommand):
    help = "Create the public tenant and its domain (safe to run repeatedly)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--domain",
            default=settings.PUBLIC_DOMAIN,
            help="Hostname of the main site (default: PUBLIC_DOMAIN setting).",
        )

    def handle(self, *args, domain, **options):
        tenant = ensure_public_tenant(domain)
        self.stdout.write(self.style.SUCCESS(f"Public tenant ready: {tenant} at {domain}"))
