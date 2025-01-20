from celery import shared_task
import logging

logger = logging.getLogger("xero")


@shared_task(bind=True)
def sync_accounts_task(self, xero_accounts):
    """
    Asynchronous task to sync accounts with Xero.
    """
    from workflow.api.xero.sync import sync_accounts

    try:
        logger.info("Starting async sync for accounts.")
        sync_accounts(xero_accounts)
        logger.info("Completed async sync for accounts.")
    except Exception as e:
        logger.error(f"Error in async sync for accounts: {str(e)}")
        raise self.retry(exc=e, countdown=60)
    

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


@shared_task(bind=True)
def sync_invoices_task(self, invoices):
    """
    Asynchronous task to sync Xero invoices.
    """
    from workflow.api.xero.sync import sync_invoices

    try:
        logger.info("Starting async sync for invoices.")
        sync_invoices(invoices)
        logger.info("Completed async sync for invoices.")
    except Exception as e:
        logger.error(f"Error in async sync for invoices: {str(e)}")
        raise self.retry(exc=e, countdown=60)
    

@shared_task(bind=True)
def sync_bills_task(self, bills):
    """
    Asynchronous task to sync Xero bills (ACCPAY).
    """
    from workflow.api.xero.sync import sync_bills

    try:
        logger.info("Starting async sync for bills.")
        sync_bills(bills)
        logger.info("Completed async sync for bills.")
    except Exception as e:
        logger.error(f"Error in async sync for bills: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def sync_credit_notes_task(self, notes):
    """
    Asynchronous task to sync Xero credit notes.
    """
    from workflow.api.xero.sync import sync_credit_notes

    try:
        logger.info("Starting async sync for credit notes.")
        sync_credit_notes(notes)
        logger.info("Completed async sync for credit notes.")
    except Exception as e:
        logger.error(f"Error in async sync for credit notes: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True)
def sync_journals_task(self, journals):
    """
    Asynchronous task to sync Xero journals.
    """
    from workflow.api.xero.sync import sync_journals

    try:
        logger.info("Starting async sync for journals.")
        sync_journals(journals)
        logger.info("Completed async sync for journals.")
    except Exception as e:
        logger.error(f"Error in async sync for journals: {str(e)}")
        raise self.retry(exc=e, countdown=60)
