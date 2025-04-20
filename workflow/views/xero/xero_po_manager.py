# workflow/views/xero_po_creator.py
import logging
import json
from decimal import Decimal

from django.http import JsonResponse
from django.utils import timezone

# Import base class and helpers
from .xero_base_manager import XeroDocumentManager
from .xero_helpers import format_date, clean_payload, convert_to_pascal_case

# Import models
from workflow.models import PurchaseOrder, XeroAccount, Client, Job # Add models used
from xero_python.accounting.models import LineItem, PurchaseOrder as XeroPurchaseOrder
from xero_python.exceptions import AccountingBadRequestException

logger = logging.getLogger("xero")

class XeroPurchaseOrderManager(XeroDocumentManager):
    """Simplified Xero PO sync handler"""
    _is_po_manager = True
    
    def __init__(self, purchase_order: PurchaseOrder):
        if not purchase_order.supplier:
            raise ValueError("PO must have a supplier")
        super().__init__(client=purchase_order.supplier, job=None)
        self.purchase_order = purchase_order

    def get_xero_id(self) -> str | None:
        """Returns the Xero ID if the local PO has one."""
        return str(self.purchase_order.xero_id) if self.purchase_order and self.purchase_order.xero_id else None

    def get_xero_update_method(self):
        """Returns the Xero API method for creating/updating POs."""
        # This method handles both create and update (PUT/POST)
        return self.xero_api.update_or_create_purchase_orders

    def get_local_model(self):
        """Returns the local Django model class."""
        return PurchaseOrder

    def state_valid_for_xero(self) -> bool:
        """
        Checks if the purchase order is in a valid state for Xero operations.
        For initial creation, we require 'draft' status.
        For updates, we allow any status as long as the PO has a Xero ID.
        """
        # If we're updating an existing PO in Xero, allow any status
        if self.get_xero_id():
            return True
        
        # For initial creation/sending, we require 'draft'
        return self.purchase_order.status == 'draft'

    def get_line_items(self) -> list[LineItem]:
        """
        Generates purchase order-specific LineItems for the Xero API payload.
        """
        logger.debug("Starting get_line_items for PO")
        xero_line_items = []
        account_code = None

        # Look up the Purchases account code
        try:
            # Consider making the account name/code configurable
            purchases_account = XeroAccount.objects.get(account_name__iexact="Purchases")
            account_code = purchases_account.account_code
        except XeroAccount.DoesNotExist:
            logger.warning("Could not find 'Purchases' account in Xero accounts, omitting account code for PO lines.")
        except XeroAccount.MultipleObjectsReturned:
            accounts = XeroAccount.objects.filter(account_name__iexact="Purchases")
            logger.warning(f"Found multiple 'Purchases' accounts: {[(a.account_name, a.account_code, a.xero_id) for a in accounts]}. Omitting account code.")
            # Decide if this should raise an error or just warn

        if not self.purchase_order:
             logger.error("Purchase order object is missing in get_line_items.")
             return [] # Or raise error

        for line in self.purchase_order.po_lines.all(): # Correct related name

            description = line.description
            # Prepend Job Number if available
            if line.job:
                description = f"{line.job.job_number} - {description}"

            line_item_data = {
                "description": f"Price to be confirmed - {description}" if line.price_tbc else description,
                "quantity": float(line.quantity),
                "unit_amount": float(line.unit_cost) if line.unit_cost else 0.0
            }

            # Add account code only if found
            if account_code:
                line_item_data["account_code"] = account_code

            try:
                 # Append the LineItem object directly
                 xero_line_items.append(LineItem(**line_item_data))
            except Exception as e:
                 logger.error(f"Error creating xero-python LineItem object for PO line {line.id}: {e}", exc_info=True)
                 # Decide whether to skip this line or raise the error

        logger.debug(f"Finished get_line_items for PO. Prepared {len(xero_line_items)} items.")
        return xero_line_items

    def get_xero_document(self, type="create") -> XeroPurchaseOrder:
        """
        Returns a xero_python PurchaseOrder object based on the specified type.
        """
        if not self.purchase_order:
             raise ValueError("PurchaseOrder object is missing.")

        if type == "delete":
            xero_id = self.get_xero_id()
            if not xero_id:
                raise ValueError("Cannot delete a purchase order without a Xero ID.")
            # Deletion via API usually means setting status to DELETED via update
            return XeroPurchaseOrder(
                purchase_order_id=xero_id,
                status="DELETED"
            )
        elif type in ["create", "update"]:
            # Build the common document data dictionary using snake_case keys
            document_data = {
                "purchase_order_number": self.purchase_order.po_number,
                "contact": self.get_xero_contact(), # Uses base class method
                "date": format_date(self.purchase_order.order_date),
                "line_items": self.get_line_items(),
                "status": "SUBMITTED" # TODO: Review if this should always be SUBMITTED or based on local status/action
            }

            # Add optional fields if they exist
            if self.purchase_order.expected_delivery:
                document_data["delivery_date"] = format_date(self.purchase_order.expected_delivery)
            if self.purchase_order.reference:
                document_data["reference"] = self.purchase_order.reference

            # Add the Xero PurchaseOrderID only for updates
            if type == "update":
                xero_id = self.get_xero_id()
                if not xero_id:
                    raise ValueError("Cannot update a purchase order without a Xero ID.")
                document_data["purchase_order_id"] = xero_id

            # Log the data just before creating the XeroPurchaseOrder object
            logger.debug(f"Data for XeroPurchaseOrder init: {document_data}")
            try:
                return XeroPurchaseOrder(**document_data)
            except Exception as e:
                 logger.error(f"Error initializing xero_python PurchaseOrder model: {e}", exc_info=True)
                 raise # Re-raise the error
        else:
            raise ValueError(f"Unknown document type for Purchase Order: {type}")

    def sync_to_xero(self):
        """Simplified method to sync current PO state to Xero"""
            
        try:
            # Determine if creating or updating
            action = "update" if self.get_xero_id() else "create"
            xero_doc = self.get_xero_document(type=action)
            payload = {"PurchaseOrders": [xero_doc.to_dict()]}
            
            # Call Xero API
            self.get_xero_update_method()(
                xero_tenant_id=self.xero_tenant_id,
                purchase_orders=payload
            )
            return True
            
        except Exception as e:
            logger.error(f"Xero sync failed: {e}")
            return False

    def create_document(self):
        """Legacy method - delegates to sync_to_xero"""
        success = self.sync_to_xero()
        return JsonResponse({"success": success})

    def delete_document(self):
        """
        Deletes the purchase order in Xero by setting its status to DELETED.
        Updates the local PurchaseOrder record by clearing the Xero ID.
        Returns a JsonResponse suitable for the calling view.
        """
        xero_id = self.get_xero_id()
        if not xero_id:
            logger.error(f"Cannot delete PO {self.purchase_order.id}: No Xero ID found.")
            return JsonResponse({"success": False, "error": "Purchase Order not found in Xero (no Xero ID)."}, status=404)

        logger.info(f"Attempting to delete purchase order {self.purchase_order.id} (Xero ID: {xero_id}) by setting status to DELETED.")

        try:
            # Prepare the minimal payload for deletion (setting status)
            xero_document = XeroPurchaseOrder(purchase_order_id=xero_id, status="DELETED")
            payload = convert_to_pascal_case(clean_payload(xero_document.to_dict()))
            payload_list = {"PurchaseOrders": [payload]}
            logger.debug(f"Serialized payload for delete: {json.dumps(payload_list, indent=4)}")

        except Exception as e:
            logger.error(f"Error serializing XeroDocument for delete: {str(e)}", exc_info=True)
            return JsonResponse({"success": False, "error": f"Failed to serialize data for Xero deletion: {str(e)}"}, status=500)

        try:
            # Use the update method to set the status to DELETED
            update_method = self.get_xero_update_method()
            logger.info(f"Calling Xero API method for deletion: {update_method.__name__}")
            response, http_status, http_headers = update_method(
                self.xero_tenant_id,
                purchase_orders=payload_list,
                summarize_errors=False,
                _return_http_data_only=False
            )

            logger.debug(f"Xero API Response Content (delete): {response}")
            logger.debug(f"Xero API HTTP Status (delete): {http_status}")

            # Process the response
            if response and hasattr(response, 'purchase_orders') and response.purchase_orders:
                xero_po_data = response.purchase_orders[0]

                # Check for validation errors (though less likely for a status update)
                if hasattr(xero_po_data, 'validation_errors') and xero_po_data.validation_errors:
                    error_details = "; ".join([f"{err.message}" for err in xero_po_data.validation_errors])
                    logger.error(f"Xero validation errors during delete for PO {self.purchase_order.id}: {error_details}")
                    return JsonResponse({"success": False, "error": f"Xero validation errors during delete: {error_details}"}, status=400)

                # Confirm status is DELETED (or check http_status)
                if getattr(xero_po_data, 'status', None) == 'DELETED' or http_status < 300:
                    # Clear local Xero ID and update status (optional, could just clear ID)
                    self.purchase_order.xero_id = None
                    self.purchase_order.xero_last_synced = timezone.now()
                    self.purchase_order.status = "deleted"
                    self.purchase_order.save(update_fields=['xero_id', 'xero_last_synced', 'status'])

                    logger.info(f"Successfully deleted purchase order {self.purchase_order.id} in Xero (Xero ID: {xero_id}).")
                    return JsonResponse({"success": True, "action": "delete"})
                else:
                    error_msg = f"Xero did not confirm deletion status for PO {self.purchase_order.id}. Status: {getattr(xero_po_data, 'status', 'Unknown')}"
                    logger.error(error_msg)
                    return JsonResponse({"success": False, "error": error_msg}, status=500)
            else:
                error_msg = "Unexpected or empty response from Xero API during delete."
                logger.error(f"{error_msg} for PO {self.purchase_order.id}. Response: {response}")
                return JsonResponse({"success": False, "error": error_msg}, status=500)

        except AccountingBadRequestException as e:
            error_body = {}
            error_message = str(e)
            try:
                 if hasattr(e, 'body') and e.body:
                      error_body = json.loads(e.body)
                      error_message = error_body.get('Detail', error_body.get('Message', str(e)))
            except json.JSONDecodeError:
                 logger.warning("Could not decode Xero error body JSON during delete.")

            logger.error(f"Xero API Bad Request during delete for PO {self.purchase_order.id}: {error_message} Body: {error_body}")
            return JsonResponse({"success": False, "error": f"Xero Error during delete: {error_message}"}, status=e.status)
        except Exception as e:
            logger.error(f"Unexpected error deleting PO {self.purchase_order.id} from Xero: {str(e)}", exc_info=True)
            return JsonResponse({"success": False, "error": f"An unexpected error occurred during deletion: {str(e)}"}, status=500)
