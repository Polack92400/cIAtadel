"""Celery application.

Workers process untrusted PDFs, so tasks must always receive *IDs* (never
file paths or tenant hints from clients) and re-resolve the tenant from the
database before doing any work.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("ciatadel")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
