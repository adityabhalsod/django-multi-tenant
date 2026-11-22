"""Local development: DEBUG on, debug toolbar, emails to Mailpit."""

from .base import *  # noqa: F403
from .base import INSTALLED_APPS, MAILERS, MIDDLEWARE, env

DEBUG = env.bool("DJANGO_DEBUG", default=True)

# Docker Compose runs Mailpit (web UI on http://localhost:8025).
MAILERS["default"]["OPTIONS"].update(
    host=env.str("EMAIL_HOST", default="mailpit"), port=env.int("EMAIL_PORT", default=1025)
)

if env.bool("USE_DEBUG_TOOLBAR", default=False):
    INSTALLED_APPS = [*INSTALLED_APPS, "debug_toolbar"]
    toolbar = "debug_toolbar.middleware.DebugToolbarMiddleware"
    MIDDLEWARE = [*MIDDLEWARE[:2], toolbar, *MIDDLEWARE[2:]]
    DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG}
