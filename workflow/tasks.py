import logging

from celery import shared_task

logger = logging.getLogger("xero")


@shared_task(bind=True)
def sync_client_task(self, client_id):
    """
    Asynchronous task to sync a single client with Xero.
    """
    from workflow.api.xero.sync import sync_client_to_xero
    from workflow.models.client import Client

    try:
        client = Client.objects.get(id=client_id)
        logger.info(f"Syncing client {client.name} with Xero.")
        sync_client_to_xero(client)
        logger.info(f"Client {client.name} synced successfully.")
    except Exception as e:
        logger.error(f"Error syncing client {client_id}: {str(e)}")
        raise self.retry(exc=e)
