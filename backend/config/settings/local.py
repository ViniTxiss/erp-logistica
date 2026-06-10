"""
Settings para validação local sem Docker (usa SQLite).
Só para rodar manage.py check / migrate localmente.
"""
from .base import *  # noqa
import environ

env = environ.Env()

DEBUG = True

# SQLite para dev local sem Docker
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Celery desabilitado (sem Redis)
CELERY_TASK_ALWAYS_EAGER = True

# Sem cache real
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
