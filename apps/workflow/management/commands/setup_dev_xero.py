from django.core.management.base import BaseCommand
from django.db import close_old_connections
from xero_python.identity import IdentityApi
from apps.workflow.api.xero.xero import api_client, get_valid_token
from apps.workflow.models import CompanyDefaults
from apps.workflow.api.xero.sync import synchronise_xero_data
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
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Xero sync failed: {e}"))
                logger.error(f"Error during Xero sync: {e}", exc_info=True)

        close_old_connections()
        self.stdout.write(self.style.SUCCESS("Development Xero setup completed!"))