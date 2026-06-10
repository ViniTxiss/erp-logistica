from .base import *  # noqa

DEBUG = False

# Segurança HTTPS
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Sentry (opcional — configure SENTRY_DSN no .env de prod)
import environ
env = environ.Env()
SENTRY_DSN = env("SENTRY_DSN", default=None)
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.1)
