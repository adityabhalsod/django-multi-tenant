"""Custom user model.

The ``users`` app is listed in *both* ``SHARED_APPS`` and ``TENANT_APPS``, so
every schema gets its own ``users_user`` table:

* ``public.users_user``   -> platform staff who manage tenants.
* ``<tenant>.users_user`` -> that tenant's users. Fully isolated: the same
  email can exist in two tenants and they are different accounts.

Always start a project with a custom user model; switching later is painful.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField("email address", unique=True)

    REQUIRED_FIELDS = ["email"]

    def __str__(self) -> str:
        return self.get_username()
