import os
import datetime
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core import serializers
from django.apps import apps
from faker import Faker

class Command(BaseCommand):
    help = 'Backs up necessary production data, excluding Xero-related models.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data backup...'))

        # Define models to include and exclude based on the provided strategy
        # Exclude: Models directly related to Xero integration
        EXCLUDE_MODELS = [
            'accounting.Invoice',
            'accounting.Quote',
        ]

        # Include: Models that can be copied directly or need relinkage during import
        # These will be passed to dumpdata
        INCLUDE_MODELS = [
            # Core job management
            'job.Job',
            'job.JobPricing',
            'job.JobPart', 
            'job.MaterialEntry',
            'job.AdjustmentEntry',
            'job.JobEvent',
            'job.JobFile',
            
            # Time tracking
            'timesheet.TimeEntry',
            
            # Staff data (will be anonymized)
            'accounts.Staff',
            
            # Client data (ClientContact be anonymized)
            'client.Client',
            'client.ClientContact',
            
            # Purchasing/inventory
            'purchasing.PurchaseOrder',
            'purchasing.PurchaseOrderLine', 
            'purchasing.Stock',
            
            # Quoting/supplier data
            'quoting.SupplierPriceList',
            'quoting.SupplierProduct',
        ]

        # Construct the list of models for dumpdata, excluding those explicitly marked
        # We need to ensure that only models that exist are included.
        # For simplicity, we'll assume all listed INCLUDE_MODELS exist.
        # In a real scenario, you might dynamically check `apps.get_models()`
        # to verify existence.
        models_to_dump = [model for model in INCLUDE_MODELS if model not in EXCLUDE_MODELS]

        # Define the output directory and filename
        backup_dir = os.path.join(settings.BASE_DIR, 'restore')
        os.makedirs(backup_dir, exist_ok=True) # Ensure the directory exists

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f'prod_backup_{timestamp}.json'
        output_path = os.path.join(backup_dir, output_filename)

        self.stdout.write(f'Backup will be saved to: {output_path}')
        self.stdout.write(f'Models to be backed up: {", ".join(models_to_dump)}')

        try:
            # Initialize Faker for data anonymization
            fake = Faker()
            
            # Serialize data with anonymization
            backup_data = []
            
            for model_label in models_to_dump:
                app_label, model_name = model_label.split('.')
                model = apps.get_model(app_label, model_name)
                
                self.stdout.write(f'Processing {model_label}...')
                
                for instance in model.objects.all():
                    # Serialize the instance
                    serialized = json.loads(serializers.serialize('json', [instance]))[0]
                    
                    # Anonymize PII fields based on model
                    self._anonymize_instance(serialized, model_label, fake)
                    
                    backup_data.append(serialized)
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(self.style.SUCCESS(f'Data backup completed successfully to {output_path}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during data backup: {e}'))
            # Clean up the partially created file if an error occurs
            if os.path.exists(output_path):
                os.remove(output_path)
    
    def _anonymize_instance(self, serialized, model_label, fake):
        """Anonymize PII fields in the serialized instance"""
        fields = serialized['fields']
        
        if model_label == 'accounts.Staff':
            # Anonymize staff names and emails but keep structure
            if 'first_name' in fields:
                fields['first_name'] = fake.first_name()
            if 'last_name' in fields:
                fields['last_name'] = fake.last_name()
            if 'email' in fields:
                # Keep original email format for referential integrity
                original_email = fields['email']
                if '@' in original_email:
                    domain = original_email.split('@')[1]
                    fields['email'] = f"{fake.user_name()}@{domain}"
        
        elif model_label == 'client.Client':
            # Anonymize client names
            if 'name' in fields:
                fields['name'] = fake.company()
            if 'contact_person' in fields and fields['contact_person']:
                fields['contact_person'] = fake.name()
            if 'contact_email' in fields and fields['contact_email']:
                fields['contact_email'] = fake.email()
            if 'contact_phone' in fields and fields['contact_phone']:
                fields['contact_phone'] = fake.phone_number()
        
        elif model_label == 'client.ClientContact':
            # Anonymize contact details
            if 'name' in fields:
                fields['name'] = fake.name()
            if 'email' in fields and fields['email']:
                fields['email'] = fake.email()
            if 'phone' in fields and fields['phone']:
                fields['phone'] = fake.phone_number()
        
        elif model_label == 'job.Job':
            # Anonymize job names and contact details
            if 'name' in fields:
                # Keep it somewhat realistic for jobs
                fields['name'] = f"{fake.word().capitalize()} {fake.word()}"
            if 'contact_person' in fields and fields['contact_person']:
                fields['contact_person'] = fake.name()
            if 'contact_email' in fields and fields['contact_email']:
                fields['contact_email'] = fake.email()
            if 'contact_phone' in fields and fields['contact_phone']:
                fields['contact_phone'] = fake.phone_number()