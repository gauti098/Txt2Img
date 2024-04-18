import json
from celery import shared_task
from django_celery_results.models import TaskResult
import time
from django.db import connection


@shared_task(bind=True)
def taskCheck(self,data):
    connection.close()
    try:
        _a = TaskResult.objects.all().count()
        return _a
    except Exception as e:
        return f"{self.request.id} {e}"
    return data