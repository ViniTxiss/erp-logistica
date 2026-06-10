"""
Settings para o ambiente de testes.
Usa SQLite em memória para máxima velocidade.
Não depende de arquivo .env — define variáveis mínimas antes do import.
"""
import os

# Variáveis mínimas necessárias para o base.py não quebrar
# (sobrescritas abaixo de qualquer forma, mas precisam existir)
os.environ.setdefault("SECRET_KEY", "test-secret-key-apenas-para-ci")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("REDIS_URL", "memory://")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "")
os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1")
os.environ.setdefault("ACCESS_TOKEN_LIFETIME_MINUTES", "60")
os.environ.setdefault("REFRESH_TOKEN_LIFETIME_DAYS", "7")

from .base import *  # noqa

DEBUG = True

# SQLite em memória — muito mais rápido nos testes
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Celery síncrono — sem broker necessário
CELERY_TASK_ALWAYS_EAGER = True

# Sem cache real
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Senha simples nos testes (mais rápido que bcrypt)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# DRF — apenas JSON nos testes
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa
    "rest_framework.renderers.JSONRenderer",
]

