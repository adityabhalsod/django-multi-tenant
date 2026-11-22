import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.tenants.services import (
    ProvisioningError,
    TenantAdmin,
    normalise_schema_name,
    provision_tenant,
)


class Command(BaseCommand):
    help = (
        "Create a tenant with its schema, domain and an optional admin user.\n\n"
        "Example: manage.py provision_tenant --name 'Acme' --admin-email admin@acme.test\n"
        "The domain defaults to <schema>.<PUBLIC_DOMAIN>, e.g. acme.localhost."
    )

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True)
        parser.add_argument("--schema", help="Schema name (default: derived from --name).")
        parser.add_argument("--domain", help="Hostname (default: <schema>.<PUBLIC_DOMAIN>).")
        parser.add_argument("--admin-username", default="admin")
        parser.add_argument("--admin-email", help="Create a tenant superuser with this email.")
        parser.add_argument(
            "--admin-password",
            default=os.environ.get("TENANT_ADMIN_PASSWORD"),
            help="Password for the tenant admin (or set TENANT_ADMIN_PASSWORD).",
        )

    def handle(self, *args, **opts):
        schema = opts["schema"] or normalise_schema_name(opts["name"])
        domain = opts["domain"] or f"{schema.replace('_', '-')}.{settings.PUBLIC_DOMAIN}"
        admin = None
        if opts["admin_email"]:
            if not opts["admin_password"]:
                raise CommandError("--admin-password (or TENANT_ADMIN_PASSWORD) is required")
            admin = TenantAdmin(opts["admin_username"], opts["admin_email"], opts["admin_password"])
        try:
            tenant = provision_tenant(
                name=opts["name"], schema_name=schema, domain=domain, admin=admin
            )
        except ProvisioningError as exc:
            raise CommandError(str(exc)) from exc
        port = os.environ.get("APP_PORT", "8000")
        self.stdout.write(self.style.SUCCESS(f"Tenant {tenant} ready at http://{domain}:{port}/"))
