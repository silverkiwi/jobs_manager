from job.models import JobEvent as BaseJobEvent


class JobEvent(BaseJobEvent):
    class Meta:
        proxy = True
