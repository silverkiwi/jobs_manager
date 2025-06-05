from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone
from apps.workflow.api.xero.xero import refresh_token

import logging

from apps.workflow.services.xero_sync_service import XeroSyncService
from apps.workflow.api.xero.sync import synchronise_xero_data

logger = logging.getLogger("xero")

class Command(BaseCommand):
    help = 'Triggers a manual, one-off Xero synchronization.'

    def handle(self, *args, **options):
        # Basic logging setup for a single execution command
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        logger.info("Attempting to start a manual Xero synchronization...")
        logger.info("Starting manual Xero synchronization...")
        try:
            for message in synchronise_xero_data():
                # Log messages from the sync process
                severity = message.get('severity', 'info')
                msg_text = message.get('message', 'No message')
                entity = message.get('entity', 'N/A')
                progress = message.get('progress', 'N/A')
                
                log_func = getattr(logger, severity, logger.info)
                progress_display = "N/A" if not isinstance(progress, (int, float)) else f"{progress:.2f}"
                log_func(f"Sync Progress ({entity}): {msg_text} (Progress: {progress_display})")

            logger.info("Manual Xero synchronization completed successfully.")
        except Exception as e:
            logger.error(f"Error during manual Xero synchronization: {e}", exc_info=True)
            self.stderr.write(self.style.ERROR(f"Xero sync failed: {e}")) 

        close_old_connections()
        logger.info("Manual Xero synchronization command finished.")
