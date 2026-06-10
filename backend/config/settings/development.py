from .base import *  # noqa

DEBUG = True

# Em dev, permite o BrowsableAPI do DRF
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

# Django Debug Toolbar
INSTALLED_APPS += ["debug_toolbar"]  # noqa
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]  # noqa
INTERNAL_IPS = ["127.0.0.1"]

# Email no terminal
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
