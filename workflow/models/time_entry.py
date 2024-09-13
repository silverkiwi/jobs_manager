import uuid

from django.db import models

from workflow.models import Job, JobPricingType, Staff


class TimeEntry(models.Model):
    id: models.UUIDField = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    job: Job = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="time_entries"
    )  # type: ignore
    job_pricing: JobPricingType = models.ForeignKey(
        JobPricingType,
        on_delete=models.CASCADE,
        related_name="time_entries",
        null=True,
        blank=True,
    )  # type: ignore
    staff: Staff = models.ForeignKey(
        "Staff", on_delete=models.CASCADE, related_name="time_entries"
    )  # type: ignore
    date: models.DateField = models.DateField()
    minutes: models.DecimalField = models.DecimalField(
        max_digits=5, decimal_places=2
    )  # Duration in minutes
    note: models.TextField = models.TextField(blank=True, null=True)
    is_billable: models.BooleanField = models.BooleanField(default=True)
    wage_rate: models.DecimalField = models.DecimalField(
        max_digits=10, decimal_places=2
    )
    charge_out_rate: models.DecimalField = models.DecimalField(
        max_digits=10, decimal_places=2
    )

    @property
    def cost(self) -> float:
        return self.hours * self.wage_rate  # type: ignore

    @property
    def revenue(self) -> float:
        return self.hours * self.charge_out_rate  # type: ignore

    @property
    def hours(self) -> float:
        return self.minutes / 60  # type: ignore

    def __str__(self) -> str:
        staff_name: str = self.staff.get_display_name()
        job_name: str = self.job.name
        time_date: str = self.date
        formatted_job: str = f"{staff_name} {job_name} on {time_date}"
        return formatted_job  # type: ignore
