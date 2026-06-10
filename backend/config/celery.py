import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("formuca")

# Lê configurações com prefixo CELERY_ do settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Descobre tasks em todos os apps instalados
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
