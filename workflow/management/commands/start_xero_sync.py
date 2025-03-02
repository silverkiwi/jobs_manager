from django.core.management.base import BaseCommand
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone
from django.core.cache import cache
import logging

from workflow.models.xero_token import XeroToken
from workflow.api.xero.sync import synchronise_xero_data

logger = logging.getLogger("xero")

class Command(BaseCommand):
    help = 'Starts the Xero sync scheduler that runs every hour'

    def handle(self, *args, **options):
        def xero_sync_job():
            # Check if we have a valid Xero token
            token = XeroToken.objects.first()
            if not token:
                logger.info("No Xero token found. Skipping sync.")
                return
            
            logger.info(f"Starting scheduled Xero sync at {timezone.now()}")
            synchronise_xero_data()
            logger.info(f"Completed scheduled Xero sync at {timezone.now()}")

        # Initialize the scheduler
        scheduler = BackgroundScheduler()

        # Add the job to the scheduler
        scheduler.add_job(
            xero_sync_job,
            trigger=IntervalTrigger(hours=1),
            id='xero_sync_job',
            name='Xero Sync Job',
            replace_existing=True,
            next_run_time=timezone.now()  # Run immediately on startup
        )

        try:
            logger.info("Starting Xero sync scheduler...")
            scheduler.start()
            # Keep the command running but not blocking
            while True:
                try:
                    timezone.now()  # Simple operation to check if Django is still alive
                    import time
                    time.sleep(60)  # Check every minute
                except Exception:
                    break
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down Xero sync scheduler...")
            scheduler.shutdown()