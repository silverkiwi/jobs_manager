from django.db import models
from django.utils.timezone import now

from accounts.models import Staff

from job.models import JobEvent as BaseJobEvent


class JobEvent(BaseJobEvent):
    class Meta:
        proxy = True
