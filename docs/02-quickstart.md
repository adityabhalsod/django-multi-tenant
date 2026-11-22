# 2. Quick start

Two ways to run the project. **Option A (Docker)** needs nothing but Docker. **Option B (uv)**
runs Python on your machine and is faster for day-to-day work.

> **Why `*.localhost` works without editing `/etc/hosts`:** modern browsers, curl and most
> operating systems resolve every `something.localhost` name to `127.0.0.1`. If your system
> does not, add `127.0.0.1 acme.localhost` to your hosts file.

## Option A: Docker Compose (recommended for a first run)

**Step 1. Clone and configure**

```bash
git clone https://github.com/adityabhalsod/django-multi-tenant.git
cd django-multi-tenant
cp .env.example .env          # or: make setup
```

**Step 2. Start the stack**

```bash
docker compose up -d --build  # or: make up
docker compose ps             # web should become "healthy"
```

This starts `web` (Django dev server), `worker` (Celery), `beat` (Celery scheduler),
`db` (PostgreSQL 18 with an extra `analytics` database), `redis` and `mailpit`. The web
container runs all migrations and creates the public tenant on start.

**Step 3. Create a platform admin** (manages tenants at http://localhost:8000/admin/)

```bash
docker compose exec web python manage.py create_tenant_superuser --schema=public
```

**Step 4. Create your first tenants**

```bash
make tenant NAME="Acme" EMAIL=admin@acme.test PASSWORD=change-me-123
make tenant NAME="Globex" EMAIL=admin@globex.test PASSWORD=change-me-123
```

**Step 5. Explore**

| URL | What it is |
|---|---|
| http://localhost:8000/ | Public site (schema `public`) |
| http://localhost:8000/admin/ | Platform admin: tenants and domains |
| http://acme.localhost:8000/ | Acme's workspace (schema `acme`) |
| http://acme.localhost:8000/admin/ | Acme's admin: only Acme's users and projects |
| http://acme.localhost:8000/api/docs/ | Swagger UI for the tenant API |
| http://localhost:8025/ | Mailpit: every email the app sends |

**Step 6. See isolation for yourself**

```bash
# Get a token for Acme's admin and create a project
TOKEN=$(curl -s -X POST http://acme.localhost:8000/api/auth/token/ \
  -d username=admin -d password=change-me-123 | python -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s -X POST http://acme.localhost:8000/api/projects/ -H "Authorization: Token $TOKEN" -d name=Rocket

# The same token is meaningless on Globex: users live in each tenant's schema
curl -i http://globex.localhost:8000/api/projects/ -H "Authorization: Token $TOKEN"   # 401
```

**Step 7. Optional: run with a streaming read replica**

```bash
echo "DATABASE_REPLICA_URLS=postgres://app:app@db-replica:5432/app" >> .env
docker compose --profile replica up -d
curl http://localhost:8000/health/ready/   # lists db:replica_1
```

Stop everything with `make down` (data kept) or `docker compose down -v` (data deleted).

## Option B: Local Python with uv

**Step 1. Install uv** (once): see [3. uv](03-uv.md#31-install-uv).

**Step 2. Start only the services** (or use your own PostgreSQL 14+ and Redis):

```bash
docker compose up -d db redis mailpit
```

**Step 3. Install and run**

```bash
cp .env.example .env              # points at localhost:5432 / localhost:6379
uv sync                           # creates .venv with the pinned Python + deps
uv run python manage.py migrate_schemas
uv run python manage.py migrate_extra
uv run python manage.py bootstrap_public
uv run python manage.py provision_tenant --name Acme --admin-email admin@acme.test --admin-password change-me-123
uv run python manage.py runserver
```

In another terminal: `uv run celery -A config worker -l info`.

**Step 4. Run the tests**

```bash
uv run pytest
```

Next: [3. uv](03-uv.md)
