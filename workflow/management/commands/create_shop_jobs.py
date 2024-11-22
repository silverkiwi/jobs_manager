import uuid
import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from workflow.models import Job, Client

class Command(BaseCommand):
    help = 'Create shop jobs for internal purposes'

    def handle(self, *args, **kwargs):
        # Define shop job details
        shop_jobs = [
            {"name": "Business Development", "description": "Sales without a specific client"},
            {"name": "Bench - busy work", "description": "Bench work and other busy tasks not directly tied to client jobs"},
            {"name": "Worker Admin", "description": "Mask fittings, meetings, and other worker-related admin"},
            {"name": "Office Admin", "description": "General office administration tasks"},
            {"name": "Annual Leave", "description": "Annual leave taken by workers"},
            {"name": "Sick Leave", "description": "Sick leave taken by workers"},
            {"name": "Other Leave", "description": "Other types of leave taken by workers"},
            {"name": "Travel", "description": "Travel for work purposes"},
            {"name": "Training", "description": "Training sessions for upskilling workers"},
        ]

        # Get the shop client
        shop_client = Client.objects.get(name="MSM (Shop)")

        # Iterate through the shop jobs and create them
        for idx, job_details in enumerate(shop_jobs, start=1):
            # Create the job instance
            job = Job(
                name=job_details["name"],
                client=shop_client,
                contact_person="Corrin Lakeland",
                description="",
                material_gauge_quantity=job_details["description"], # We put description here, so Kanban doesn't show it
                status="special",
                shop_job=True,
                job_is_valid=True,
                paid=False,
                charge_out_rate=0.00,
            )
            job.save()

        self.stdout.write(self.style.SUCCESS('Shop jobs have been successfully created.'))