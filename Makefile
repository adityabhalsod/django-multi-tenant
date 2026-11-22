# Developer shortcuts. Run `make help` to list them.
# Docker targets talk to the compose stack; `local-*` targets use uv on your machine.

COMPOSE ?= docker compose
RUN     := $(COMPOSE) exec web
NAME    ?= Acme
EMAIL   ?= admin@example.com
PASSWORD ?= admin12345

.DEFAULT_GOAL := help
.PHONY: help setup up down restart logs ps shell dbshell migrate makemigrations tenant \
        tenants superuser test lint format check build prod-up prod-down \
        local-install local-run local-worker local-test

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## First run: create .env from the example (does not overwrite)
	@test -f .env || cp .env.example .env
	@echo ".env ready. Next: make up"

# --- Docker (development) -----------------------------------------------------
up: setup ## Build and start the dev stack in the background
	$(COMPOSE) up -d --build
	@echo "Public site: http://localhost:8000   Mailpit: http://localhost:8025"

down: ## Stop the dev stack (keeps data volumes)
	$(COMPOSE) down

restart: ## Restart app containers (web, worker, beat)
	$(COMPOSE) restart web worker beat

logs: ## Follow logs of every service
	$(COMPOSE) logs -f

ps: ## Show container status
	$(COMPOSE) ps

shell: ## Django shell (inside the web container)
	$(RUN) python manage.py shell

dbshell: ## psql on the primary database
	$(COMPOSE) exec db psql -U $${POSTGRES_USER:-app} $${POSTGRES_DB:-app}

migrate: ## Migrate public schema, every tenant schema and the extra databases
	$(RUN) python manage.py migrate_schemas
	$(RUN) python manage.py migrate_extra

makemigrations: ## Create migrations for changed models
	$(RUN) python manage.py makemigrations

tenant: ## Create a tenant: make tenant NAME="Acme" EMAIL=admin@acme.test PASSWORD=...
	$(RUN) python manage.py provision_tenant --name "$(NAME)" --admin-email "$(EMAIL)" --admin-password "$(PASSWORD)"

tenants: ## List tenants and their domains
	$(RUN) python manage.py shell -v 0 -c "from apps.tenants.models import Domain; [print(f'{d.tenant.schema_name:20} http://{d.domain}:8000') for d in Domain.objects.select_related('tenant')]"

superuser: ## Create a platform (public schema) superuser
	$(RUN) python manage.py create_tenant_superuser --schema=public

test: ## Run the test suite in the container
	$(RUN) pytest

build: ## Build the production image
	docker build --target production -t django-multi-tenant:latest .

prod-up: ## Start the production-like stack (needs .env.prod)
	$(COMPOSE) -f compose.prod.yaml --env-file .env.prod up -d --build

prod-down: ## Stop the production-like stack
	$(COMPOSE) -f compose.prod.yaml --env-file .env.prod down

# --- Local (uv, no Docker for Python) ---------------------------------------
local-install: ## Install Python + dependencies with uv and set up pre-commit
	uv sync
	uv run pre-commit install

local-run: ## Run the dev server locally (needs PostgreSQL + Redis)
	uv run python manage.py migrate_schemas
	uv run python manage.py migrate_extra
	uv run python manage.py bootstrap_public
	uv run python manage.py runserver

local-worker: ## Run a Celery worker locally
	uv run celery -A config worker --loglevel=INFO

local-test: ## Run tests locally
	uv run pytest

lint: ## Lint with ruff
	uv run ruff check .
	uv run ruff format --check .

format: ## Auto-format and fix lint issues
	uv run ruff check --fix .
	uv run ruff format .

check: lint local-test ## Lint + tests (what CI runs)
