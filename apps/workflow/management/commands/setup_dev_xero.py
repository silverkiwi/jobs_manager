from django.core.management.base import BaseCommand
from django.db import close_old_connections
from xero_python.identity import IdentityApi
from apps.workflow.api.xero.xero import api_client, get_valid_token
from apps.workflow.models import CompanyDefaults
from apps.workflow.api.xero.sync import synchronise_xero_data
from apps.client.models import Client
import logging

logger = logging.getLogger("xero")


class Command(BaseCommand):
    help = "Setup Xero for development by connecting to Demo Company and running initial sync"

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-sync',
            action='store_true',
            help='Skip the initial Xero sync after setting up tenant ID',
        )

    def handle(self, *args, **options):
        # Setup logging
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        self.stdout.write(self.style.SUCCESS("Setting up Xero for development..."))

        # Step 1: Check for valid token
        token = get_valid_token()
        if not token:
            self.stdout.write(
                self.style.ERROR(
                    "No valid Xero token found. Please authenticate with Xero first by visiting the app."
                )
            )
            return

        # Step 2: Get available tenants
        identity_api = IdentityApi(api_client)
        connections = identity_api.get_connections()

        # Step 3: Find Demo Company
        demo_tenant_id = None
        for conn in connections:
            if "Demo Company" in conn.tenant_name:
                demo_tenant_id = conn.tenant_id
                self.stdout.write(
                    self.style.SUCCESS(f"Found Demo Company: {conn.tenant_name} ({demo_tenant_id})")
                )
                break

        if not demo_tenant_id:
            self.stdout.write(self.style.ERROR("Demo Company not found in available Xero connections."))
            self.stdout.write("Available organizations:")
            for conn in connections:
                self.stdout.write(f"  - {conn.tenant_name} ({conn.tenant_id})")
            return

        # Step 4: Update CompanyDefaults
        try:
            company = CompanyDefaults.objects.first()
            if not company:
                self.stdout.write(self.style.ERROR("No CompanyDefaults found. Please create one first."))
                return
            
            old_tenant_id = company.xero_tenant_id
            company.xero_tenant_id = demo_tenant_id
            company.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Updated CompanyDefaults Xero tenant ID from {old_tenant_id} to {demo_tenant_id}"
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to update CompanyDefaults: {e}"))
            return

        # Step 5: Run initial sync (unless skipped)
        if options['skip_sync']:
            self.stdout.write(self.style.WARNING("Skipping initial Xero sync as requested."))
        else:
            self.stdout.write(self.style.SUCCESS("Starting initial Xero sync..."))
            try:
                sync_count = 0
                for message in synchronise_xero_data():
                    sync_count += 1
                    # Only show progress messages every 100 items to avoid spam
                    if sync_count % 100 == 0:
                        severity = message.get("severity", "info")
                        msg_text = message.get("message", "No message")
                        entity = message.get("entity", "N/A")
                        progress = message.get("progress", "N/A")
                        
                        progress_display = (
                            "N/A"
                            if not isinstance(progress, (int, float))
                            else f"{progress:.2f}"
                        )
                        self.stdout.write(f"Sync Progress ({entity}): {msg_text} (Progress: {progress_display})")

                self.stdout.write(self.style.SUCCESS("Initial Xero sync completed successfully."))
                
                # Fix shop client to have correct Xero ID
                self._fix_shop_client_xero_id()
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Xero sync failed: {e}"))
                logger.error(f"Error during Xero sync: {e}", exc_info=True)

        close_old_connections()
        self.stdout.write(self.style.SUCCESS("Development Xero setup completed!"))

    def _fix_shop_client_xero_id(self):
        """
        After Xero sync, find the Demo Company Shop client and update the
        shop_client_id constant in services.py to match its UUID.
        """
        try:
            # Find the client synced from Xero with name ending exactly with " Shop"
            shop_client = Client.objects.filter(
                name__endswith=' Shop',
                xero_contact_id__isnull=False
            ).first()
            
            if not shop_client:
                self.stdout.write(self.style.WARNING("No client ending with ' Shop' found from Xero sync"))
                return
            
            shop_client_uuid = str(shop_client.id)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Found shop client: {shop_client.name} with UUID: {shop_client_uuid}"
                )
            )
            
            # Update the shop_client_id constant in services.py
            services_file_path = 'apps/accounting/services.py'
            
            try:
                with open(services_file_path, 'r') as f:
                    content = f.read()
                
                # Replace the old shop_client_id
                old_line = 'shop_client_id: str = "00000000-0000-0000-0000-000000000001" # FIXME: This must be replaced with the actual shop client ID'
                new_line = f'shop_client_id: str = "{shop_client_uuid}"  # Updated by setup_dev_xero'
                
                if old_line in content:
                    content = content.replace(old_line, new_line)
                    
                    with open(services_file_path, 'w') as f:
                        f.write(content)
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Updated shop_client_id in services.py to: {shop_client_uuid}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING("Could not find shop_client_id line to update in services.py")
                    )
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error updating services.py: {e}"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error finding shop client: {e}"))