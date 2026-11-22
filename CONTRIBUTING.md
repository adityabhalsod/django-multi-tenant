# Contributing

Thanks for helping make this boilerplate better! Bug reports, docs fixes and features are
all welcome.

## Set up in two minutes

```bash
git clone https://github.com/<you>/django-multi-tenant.git && cd django-multi-tenant
cp .env.example .env
docker compose up -d db redis     # PostgreSQL + Redis
uv sync                           # Python + dependencies
uv run pre-commit install         # lint on every commit
uv run pytest                     # should be green
```

## Workflow

1. Open an issue first for anything larger than a small fix, so we can agree on the approach.
2. Create a branch: `git checkout -b feat/short-description`.
3. Make the change **with tests**. Isolation-related changes need a test in
   `apps/projects/tests/test_api.py::TenantIsolationTests` or similar.
4. Update the relevant guide in `docs/` when behaviour or configuration changes.
5. Run `make check` (ruff + tests) and, for model changes,
   `uv run python manage.py makemigrations --check`.
6. Open a pull request using the template.

## Conventions

* Python 3.13, formatted and linted with Ruff (`make format`).
* Business logic in `services.py`, not in views or management commands.
* Settings come from environment variables; document new ones in `.env.example` and
  `docs/05-configuration.md`.
* Commit messages: [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `chore:` ...).

## Good first contributions

* More examples in `docs/`, translations of the guides
* Kubernetes / Helm manifests
* A sign-up flow that provisions tenants through Celery
* Optional `django-tenant-users` integration
