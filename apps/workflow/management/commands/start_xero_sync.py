from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone
from apps.workflow.api.xero.xero import refresh_token

import logging

from apps.workflow.models.xero_token import XeroToken
from apps.workflow.services.xero_sync_service import XeroSyncService

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
        task_id, is_new = XeroSyncService.start_sync()

        if is_new:
            logger.info(f"Manual Xero sync initiated successfully: {task_id}")
        else:
            logger.info(f"Manual Xero sync skipped (already running or recently completed): {task_id}")

        close_old_connections()
        logger.info("Manual Xero synchronization command finished.")
