import json
import os
from django.core.management.base import BaseCommand
from django.core import serializers
from django.apps import apps
from django.conf import settings
from django.db import transaction

# Define the order in which models should be loaded to respect foreign key dependencies
LOAD_ORDER = [
    # Staff data first (referenced by many models)
    'accounts.staff',
    
    # Client data (referenced by jobs)
    'client.client',
    'client.clientcontact',
    
    # Core job management
    'job.job',
    'job.jobpricing', 
    'job.jobpart',
    
    # Purchasing (PurchaseOrder before PurchaseOrderLine, both before MaterialEntry)
    'purchasing.purchaseorder',
    'purchasing.purchaseorderline',
    'purchasing.stock',
    
    # Job entries (depend on JobPricing, PurchaseOrderLine, Stock)
    'job.materialentry',
    'job.adjustmententry',
    'job.jobevent',
    'timesheet.timeentry',
    'job.jobfile',
    
    # Quoting (SupplierPriceList before SupplierProduct)
    'quoting.supplierpricelist',
    'quoting.supplierproduct',
]

# Define the order in which models should be deleted to respect foreign key dependencies
DELETION_ORDER = [
    # Quoting data (children first)
    'quoting.supplierproduct',
    'quoting.supplierpricelist',
    
    # Job entries (delete before their parents)
    'job.jobfile',
    'timesheet.timeentry',
    'job.jobevent',
    'job.adjustmententry',
    'job.materialentry',
    'job.jobpart',
    'job.jobpricing',
    
    # Purchasing (children before parents)
    'purchasing.purchaseorderline',
    'purchasing.stock',
    'purchasing.purchaseorder',
    
    # Core models (children before parents)
    'job.job',
    'client.clientcontact',
    'client.client',
    'accounts.staff',
]


class Command(BaseCommand):
    help = 'Restores data from a JSON backup file into the development environment.'

    def add_arguments(self, parser):
        parser.add_argument('backup_file', type=str, help='Path to the backup JSON file.')

    def handle(self, *args, **options):
        backup_file_path = options['backup_file']

        self.stdout.write(self.style.SUCCESS(f'Starting data restoration from {backup_file_path}'))

        with open(backup_file_path, 'r', encoding='utf-8') as f:
            raw_backup_data = json.load(f)

        # Transform the list of raw data into a dictionary keyed by model label
        backup_data = {}
        for item in raw_backup_data:
            model_label = item['model']
            if model_label not in backup_data:
                backup_data[model_label] = []
            backup_data[model_label].append(item)

        self.stdout.write(self.style.MIGRATE_HEADING('Starting pre-load data deletion...'))

        with transaction.atomic():
            for model_label in DELETION_ORDER:
                if model_label not in backup_data:
                    continue
                app_label, model_name = model_label.split('.')
                model = apps.get_model(app_label, model_name)
                self.stdout.write(f"Deleting all existing records for model: {model_label}...")
                deleted_count, _ = model.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f"Successfully deleted {deleted_count} records from {model_label}."))

        self.stdout.write(self.style.SUCCESS('Pre-load data deletion completed.'))

        # Store JobFile instances to create dummy files later
        job_files_to_create = []

        with transaction.atomic():
            # Load data
            self.stdout.write(self.style.MIGRATE_HEADING('Loading data into development environment...'))

            for model_label in LOAD_ORDER:
                if model_label not in backup_data:
                    continue
                
                model_data = backup_data[model_label]
                self.stdout.write(self.style.MIGRATE_HEADING(f"Creating {model_label} ({len(model_data)} records)"))
                
                # Use Django's deserializer
                for deserialized_obj in serializers.deserialize('json', json.dumps(model_data)):
                    # Handle JobFile file paths - files don't exist in dev so create dummy files
                    if model_label == 'job.jobfile' and hasattr(deserialized_obj.object, 'file') and deserialized_obj.object.file:
                        job_files_to_create.append({
                            'old_id': deserialized_obj.object.pk,
                            'original_path': str(deserialized_obj.object.file)
                        })
                        deserialized_obj.object.file = ''
                    
                    deserialized_obj.save()
                    self.stdout.write(f"  Created {model_label}: {deserialized_obj.object.pk}")
                
                self.stdout.write(self.style.SUCCESS(f"Completed {model_label}: {len(model_data)} records"))
            
            # Create dummy files
            if job_files_to_create:
                self.stdout.write(self.style.MIGRATE_HEADING('Creating dummy physical files for JobFile instances...'))

                for job_file_info in job_files_to_create:
                    original_path = job_file_info['original_path']
                    old_id = job_file_info['old_id']

                    relative_path = original_path.lstrip('/')
                    dummy_file_path = os.path.join(settings.MEDIA_ROOT, relative_path)

                    os.makedirs(os.path.dirname(dummy_file_path), exist_ok=True)

                    with open(dummy_file_path, 'w') as f:
                        f.write(f"This is a dummy file for JobFile with original path: {original_path}\n")
                        f.write(f"Restored from old ID: {old_id}\n")
                    self.stdout.write(f"Created dummy file: {dummy_file_path}")

        self.stdout.write(self.style.SUCCESS('Data restoration completed successfully.'))
        
        # Create defaultadmin@example.com user as per fixture
        self.stdout.write(self.style.MIGRATE_HEADING('Creating defaultadmin@example.com user...'))
        from apps.accounts.models import Staff
        
        admin_email = 'defaultadmin@example.com'
        if not Staff.objects.filter(email=admin_email).exists():
            Staff.objects.create(
                email=admin_email,
                first_name='Default',
                last_name='Admin',
                preferred_name=None,
                wage_rate='40.00',
                hours_mon='8.0',
                hours_tue='8.0',
                hours_wed='8.0',
                hours_thu='8.0',
                hours_fri='8.0',
                hours_sat='0.00',
                hours_sun='0.00',
                ims_payroll_id='ADMIN-001',
                is_active=True,
                is_staff=True,
                is_superuser=True,
                password='pbkdf2_sha256$870000$5Nw3RUuFaZZPCkeyVOm4kx$Attep1SqGF6ymdwm44LOte4wwszqte0W5ey3xcENFAI=',
                date_joined='2024-01-01T00:00:00Z',
                created_at='2024-01-01T00:00:00Z',
                updated_at='2024-01-01T00:00:00Z'
            )
            self.stdout.write(self.style.SUCCESS(f'Created defaultadmin@example.com user'))
        else:
            self.stdout.write(self.style.SUCCESS(f'defaultadmin@example.com user already exists'))