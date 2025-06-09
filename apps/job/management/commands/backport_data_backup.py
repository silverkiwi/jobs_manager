import os
import datetime
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings

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
            'job.Job',
            'timesheet.TimeEntry',
            'job.JobFile',
            'job.JobPart',
            'job.MaterialEntry',
            'job.AdjustmentEntry',
            'job.JobEvent',
            'job.JobPricing',
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
            # Call Django's dumpdata command
            # --indent=2 for readability
            # --natural-foreign and --natural-primary for better cross-database compatibility
            # (though dumpdata handles FKs by default, these can help with custom primary keys)
            call_command(
                'dumpdata',
                *models_to_dump,
                output=output_path,
                indent=2,
                natural_foreign=True,
                natural_primary=True,
                # Use the 'default' database alias, assuming production is configured there
                # or a specific 'production' alias could be used if available.
                # For this task, we assume 'default' connects to production.
                database='default',
                # Exclude contenttypes and auth.permission as they are usually not needed
                # and can cause issues with natural keys if not handled carefully.
                # Also exclude sessions and admin logs.
                exclude=['contenttypes', 'auth.permission', 'admin.logentry', 'sessions.session'],
            )
            self.stdout.write(self.style.SUCCESS(f'Data backup completed successfully to {output_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during data backup: {e}'))
            # Clean up the partially created file if an error occurs
            if os.path.exists(output_path):
                os.remove(output_path)