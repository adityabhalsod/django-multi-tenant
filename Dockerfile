# syntax=docker/dockerfile:1.7
#
# Multi-stage image built with uv.
#   docker build --target development -t dmt:dev .
#   docker build --target production  -t dmt:prod .
# See docs/04-docker.md for a walkthrough of every stage.

ARG PYTHON_VERSION=3.13
ARG UV_VERSION=0.13

# ---- uv binary (pinned minor version, copied, never installed with pip) ----
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# ---- common base ------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"
WORKDIR /app

# ---- dependencies only (cached until pyproject.toml / uv.lock change) ------
FROM base AS deps
COPY --from=uv /uv /uvx /usr/local/bin/
ARG UV_EXTRAS=""
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project ${UV_EXTRAS}

FROM deps AS deps-dev
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project ${UV_EXTRAS}

# ---- runtime base: non-root user ---------------------------------------------
FROM base AS runtime
ARG APP_UID=1000
ARG APP_GID=1000
RUN groupadd --gid ${APP_GID} app \
    && useradd --uid ${APP_UID} --gid app --home-dir /app --shell /usr/sbin/nologin app \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R app:app /app
COPY --chmod=755 docker/entrypoint.sh /usr/local/bin/entrypoint
ENTRYPOINT ["entrypoint"]
EXPOSE 8000

# ---- development: dev dependencies + uv, source is bind-mounted -------------
FROM runtime AS development
ENV DJANGO_SETTINGS_MODULE=config.settings.local
COPY --from=uv /uv /uvx /usr/local/bin/
COPY --from=deps-dev /opt/venv /opt/venv
COPY --chown=app:app . .
USER app
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---- production: slim, immutable, static files collected at build time ------
FROM runtime AS production
ENV DJANGO_SETTINGS_MODULE=config.settings.production
COPY --from=deps /opt/venv /opt/venv
COPY --chown=app:app . .
# collectstatic needs settings to import; these values are build-time dummies.
RUN DJANGO_SECRET_KEY=collectstatic-only \
    DATABASE_URL=postgres://build:build@localhost:5432/build \
    python manage.py collectstatic --noinput \
    && chown -R app:app /app/staticfiles
USER app
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live/', timeout=4).status == 200 else 1)"
CMD ["gunicorn", "config.wsgi:application", "--config", "docker/gunicorn.conf.py"]
