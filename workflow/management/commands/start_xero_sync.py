from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone
from workflow.api.xero.xero import refresh_token

import logging
import os

from workflow.models.xero_token import XeroToken
from workflow.services.xero_sync_service import XeroSyncService

logger = logging.getLogger("xero")
_scheduler = None

def get_scheduler():
    return _scheduler

class Command(BaseCommand):
    help = 'Starts the Xero sync scheduler with token refresh heartbeat'

    def handle(self, *args, **options):
        global _scheduler

        # --- Logging setup ---
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled for Xero sync process")

        # --- Heartbeat job ---
        def token_heartbeat():
            try:
                close_old_connections()
                token = XeroToken.objects.first()
                if not token:
                    logger.debug("No Xero token found. Skipping refresh.")
                    return
                logger.debug("Running token heartbeat - refreshing Xero token")
                # Only refresh token, not a full sync
                refresh_token()
                logger.debug("Token heartbeat completed")
            except Exception as e:
                logger.error(f"Error in token heartbeat: {e}")

        # --- Sync job ---
        def xero_sync_job():
            task_id, is_new = XeroSyncService.start_sync()
            if is_new:
                logger.info(f"Started scheduled Xero sync: {task_id}")
            else:
                logger.info(f"Skipped scheduled Xero sync (already running): {task_id}")

        # Interval configuration
        sync_interval_hours = int(os.getenv('XERO_SYNC_INTERVAL_HOURS', '1'))
        logger.info(f"Configuring Xero sync to run every {sync_interval_hours} hour(s)")

        _scheduler = BackgroundScheduler()

        _scheduler.add_job(
            token_heartbeat,
            trigger=IntervalTrigger(minutes=5),
            id='xero_token_heartbeat',
            name='Xero Token Heartbeat',
            replace_existing=True,
            max_instances=1,
            next_run_time=timezone.now()
        )

        _scheduler.add_job(
            xero_sync_job,
            trigger=IntervalTrigger(hours=sync_interval_hours),
            id='xero_sync_job',
            name='Xero Sync Job',
            replace_existing=True,
            max_instances=1,
            next_run_time=timezone.now()
        )

        _scheduler.start()
        logger.info("Started Xero scheduler with token heartbeat")

        try:
            while True:
                pass
        except (KeyboardInterrupt, SystemExit):
            _scheduler.shutdown()
