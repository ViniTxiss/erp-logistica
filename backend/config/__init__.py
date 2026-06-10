# Este import garante que o app Celery é carregado quando o Django sobe
from .celery import app as celery_app

__all__ = ("celery_app",)
