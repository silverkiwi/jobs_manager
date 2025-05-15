from job.models import JobFile as BaseJobFile


class JobFile(BaseJobFile):
    class Meta:
        proxy = True
