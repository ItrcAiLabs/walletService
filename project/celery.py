# project/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

app = Celery("project")
# مهم: namespace=CELERY باعث می‌شود کلیدهای CELERY_* به تنظیمات Celery مپ شوند
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
