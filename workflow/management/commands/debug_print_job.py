from django.core.management.base import BaseCommand
from workflow.models import Job, JobPricing


class Command(BaseCommand):
    help = "Debug and print job details by ID"

    def add_arguments(self, parser):
        parser.add_argument("job_id", type=str, help="ID of the job to debug")

    def handle(self, *args, **kwargs):
        job_id = kwargs["job_id"]

        # Get the job
        job = Job.objects.get(id=job_id)

        # Pricing stages to iterate over
        pricing_stages = ["estimate", "quote", "reality"]

        # Loop through each pricing stage and print the details
        for stage in pricing_stages:
            job_pricing = JobPricing.objects.get(job=job, pricing_stage=stage)
            self.stdout.write(f"\n=== {stage.capitalize()} ===")

            # General Pricing Information
            self.stdout.write(f"Job Pricing Stage: {job_pricing.pricing_stage}")

            # Print Material Entries
            for material in job_pricing.material_entries.all():
                self.stdout.write(
                    f"Material - Description: {material.description}, Quantity: {material.quantity}, Unit Cost: {material.unit_cost}, Unit Revenue: {material.unit_revenue}"
                )

            # Print Time Entries
            for time in job_pricing.time_entries.all():
                self.stdout.write(
                    f"Time Entry - Description: {time.description}, Items: {time.items}, Minutes: {time.minutes}, Hours: {time.hours}, Cost: {time.cost}, Revenue: {time.revenue}"
                )

            # Print Adjustment Entries
            for adjustment in job_pricing.adjustment_entries.all():
                self.stdout.write(
                    f"Adjustment - Description: {adjustment.description}, Cost Adjustment: {adjustment.cost_adjustment}, Price Adjustment: {adjustment.price_adjustment}"
                )

        # General Job Information
        self.stdout.write(f"\n=== General Job Information ===")
        self.stdout.write(
            f"Job: {job.name}, Job Number: {job.job_number}, Status: {job.status}, Paid: {job.paid}"
        )
