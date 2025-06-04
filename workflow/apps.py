import logging
import os
from datetime import datetime
from django.apps import AppConfig
from django.conf import settings
from django.db import close_old_connections
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from workflow.models.xero_token import XeroToken
from workflow.services.xero_sync_service import XeroSyncService

logger = logging.getLogger(__name__)

class WorkflowConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "workflow"

    def ready(self):
        # Prevent scheduler from running multiple times, especially during development
        # or when running management commands like runserver.
        # RUN_MAIN is set by Django in the main process.
        if settings.DEBUG and os.environ.get('RUN_MAIN') != 'true':
            logger.info("Skipping APScheduler setup in debug child process.")
            return

        # Only start the scheduler if it hasn't been started already
        if not hasattr(self, 'xero_scheduler_started'):
            self.xero_scheduler_started = True
            logger.info("Starting APScheduler for Xero-related jobs...")

            scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
            scheduler.add_jobstore(DjangoJobStore(), "default")

            # Clear old jobs to prevent duplicates on restart
            scheduler.remove_all_jobs()

            # Xero Heartbeat: Refresh Xero API token every 5 minutes
            scheduler.add_job(
                self.xero_heartbeat_job,
                trigger='interval',
                minutes=5,
                id='xero_heartbeat',
                max_instances=1,
                replace_existing=True,
                misfire_grace_time=60, # 1 minute grace time
                coalesce=True,
            )
            logger.info("Added 'xero_heartbeat' job to scheduler.")

            # Xero Regular Sync: Perform full Xero synchronization every 1 hour
            scheduler.add_job(
                self.xero_regular_sync_job,
                trigger='interval',
                hours=1,
                id='xero_regular_sync',
                max_instances=1,
                replace_existing=True,
                misfire_grace_time=60*60, # 1 hour grace time
                coalesce=True,
            )
            logger.info("Added 'xero_regular_sync' job to scheduler.")

            # Xero 30-Day Sync: Perform full Xero synchronization on the first day of every month at 2 AM NZT
            scheduler.add_job(
                self.xero_30_day_sync_job,
                trigger='cron',
                day='1',
                hour=2,
                minute=0,
                timezone='Pacific/Auckland', # Explicitly set NZT
                id='xero_30_day_sync',
                max_instances=1,
                replace_existing=True,
                misfire_grace_time=24*60*60, # 24 hour grace time
                coalesce=True,
            )
            logger.info("Added 'xero_30_day_sync' job to scheduler.")

            try:
                scheduler.start()
                logger.info("APScheduler started successfully for Xero-related jobs.")
            except Exception as e:
                logger.error(f"Error starting APScheduler for Xero jobs: {e}", exc_info=True)

    def xero_heartbeat_job(self):
        """
        Refreshes the Xero API token.
        """
        logger.info(f"Running Xero Heartbeat job at {datetime.now()}.")
        try:
            close_old_connections()
            XeroToken.refresh_xero_token()
            logger.info("Xero API token refreshed successfully.")
        except Exception as e:
            logger.error(f"Error during Xero Heartbeat job: {e}", exc_info=True)

    def xero_regular_sync_job(self):
        """
        Performs a full Xero synchronization.
        """
        logger.info(f"Running Xero Regular Sync job at {datetime.now()}.")
        try:
            close_old_connections()
            XeroSyncService.start_sync()
            logger.info("Xero regular sync completed successfully.")
        except Exception as e:
            logger.error(f"Error during Xero Regular Sync job: {e}", exc_info=True)

    def xero_30_day_sync_job(self):
        """
        Performs a full Xero synchronization for the 30-day sync.
        """
        logger.info(f"Running Xero 30-Day Sync job at {datetime.now()}.")
        try:
            close_old_connections()
            XeroSyncService.start_sync()
            logger.info("Xero 30-day sync completed successfully.")
        except Exception as e:
            logger.error(f"Error during Xero 30-Day Sync job: {e}", exc_info=True)