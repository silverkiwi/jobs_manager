import logging
import os
from django.apps import AppConfig
from django.conf import settings
from django.core.management import call_command
from apscheduler.schedulers.background import BackgroundScheduler
from django.db import close_old_connections

logger = logging.getLogger(__name__)

class QuotingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "quoting"

    def ready(self):
        # Ensure Django is ready before starting the scheduler
        # This check prevents the scheduler from starting multiple times
        # or before the Django app registry is fully populated.
        if settings.DEBUG and os.environ.get('RUN_MAIN') != 'true':
            # In debug mode, Django's runserver often reloads code,
            # causing ready() to be called multiple times.
            # RUN_MAIN is a flag set by Django to indicate the main process.
            # We only want to run the scheduler in the main process.
            logger.info("Skipping scraper scheduler setup in debug child process.")
            return

        # Only start the scheduler if it hasn't been started already
        # This is a simple check to prevent multiple scheduler instances
        # in production environments where ready() might still be called more than once.
        if not hasattr(self, 'scraper_scheduler_started'):
            self.scraper_scheduler_started = True
            logger.info("Starting APScheduler for scraper jobs...")
            
            from django_apscheduler.jobstores import DjangoJobStore
            from django_apscheduler.models import DjangoJobExecution
            
            scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
            scheduler.add_jobstore(DjangoJobStore(), "default")

            # Clear old jobs to prevent duplicates on restart
            scheduler.remove_all_jobs()

            # Schedule the scraper job to run every Sunday at 3 PM NZT
            scheduler.add_job(
                self.run_all_scrapers_job,
                trigger='cron',
                day_of_week='sun',
                hour=15, # 3 PM
                minute=0,
                id='run_all_scrapers_weekly',
                max_instances=1,
                replace_existing=True,
                misfire_grace_time=60*60, # 1 hour grace time for missed runs
                coalesce=True, # Only run once if multiple triggers fire
            )
            logger.info("Added 'run_all_scrapers_weekly' job to scheduler.")

            # Add a job to clean up old job executions
            scheduler.add_job(
                self.delete_old_job_executions,
                trigger='interval',
                days=1,
                id='delete_old_job_executions',
                max_instances=1,
                replace_existing=True,
                misfire_grace_time=60*60,
                coalesce=True,
            )
            logger.info("Added 'delete_old_job_executions' job to scheduler.")

            try:
                scheduler.start()
                logger.info("APScheduler started successfully for scraper jobs.")
            except Exception as e:
                logger.error(f"Error starting APScheduler for scraper jobs: {e}", exc_info=True)

    def run_all_scrapers_job(self):
        """
        This job runs the Django management command to execute all scrapers.
        """
        logger.info("Attempting to run all scrapers via scheduled job.")
        try:
            close_old_connections() # Close old DB connections to prevent issues
            call_command('run_scrapers') # This calls the existing quoting/management/commands/run_scrapers.py
            logger.info("Successfully completed scheduled scraper run.")
        except Exception as e:
            logger.error(f"Error during scheduled scraper run: {e}", exc_info=True)

    def delete_old_job_executions(self, max_age_days=7):
        """
        This job deletes entries from the DjangoJobExecution table that are older than `max_age_days`.
        It helps keep the table clean.
        """
        logger.info(f"Deleting old job executions older than {max_age_days} days.")
        DjangoJobExecution.objects.delete_old_job_executions(max_age_days)
