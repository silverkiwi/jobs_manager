from job.models import Job as BaseJob


class Job(BaseJob):
    class Meta:
        proxy = True
