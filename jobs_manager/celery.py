from celery import Celery

app = Celery("jobs_manager")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
