import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from django.conf import settings
from django.db import transaction
import random

# Define models to exclude, relink, and direct copy based on the context provided.
# These lists will guide the data restoration process.
EXCLUDE_MODELS = [
    'accounting.xeroinvoice',
    'accounting.xerocreditnote',
    'accounting.xeropayment',
    'purchasing.purchaseorderxero',
    'purchasing.purchaseorderlinexero',
    'purchasing.supplierpricelistxero',
    'purchasing.supplierproductxero',
    # Add any other Xero-related or historical models that should not be copied
]

# Define the order in which models should be loaded to respect foreign key dependencies.
# This order is crucial for successful data restoration.
LOAD_ORDER = [
    'job.job',
    'job.jobpricing', 
    'job.jobpart',
    'job.materialentry',
    'job.adjustmententry',
    'job.jobevent',
    'timesheet.timeentry',
    'job.jobfile',
    'quoting.supplierpricelist',
    'quoting.supplierproduct',
]

# Define the order in which models should be deleted to respect foreign key dependencies.
# Child models must be deleted before their parent models.
DELETION_ORDER = [
    'job.jobfile',
    'job.materialentry',
    'job.adjustmententry',
    'job.jobevent',
    'job.jobpricing',
    'timesheet.timeentry',
    'job.jobpart',
    'quoting.supplierproduct',
    'quoting.supplierpricelist',
    'job.job',
]


class Command(BaseCommand):
    help = 'Restores data from a JSON backup file into the development environment.'

    def add_arguments(self, parser):
        parser.add_argument('backup_file', type=str, help='Path to the backup JSON file.')

    def handle(self, *args, **options):
        backup_file_path = options['backup_file']

        self.stdout.write(self.style.SUCCESS(f'Starting data restoration from {backup_file_path}'))

        # Pre-check for existing Client and Staff records in the development database
        ClientModel = apps.get_model('client', 'Client')
        StaffModel = apps.get_model('accounts', 'Staff')

        # These will fail with appropriate errors if no records exist
        if not ClientModel.objects.exists():
            raise CommandError("No Client records exist in development database. Please create at least one Client first.")
        if not StaffModel.objects.exists():
            raise CommandError("No Staff records exist in development database. Please create at least one Staff first.")

        with open(backup_file_path, 'r') as f:
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
                app_label, model_name = model_label.split('.')
                model = apps.get_model(app_label, model_name)
                self.stdout.write(f"Deleting all existing records for model: {model_label}...")
                deleted_count, _ = model.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f"Successfully deleted {deleted_count} records from {model_label}."))

        self.stdout.write(self.style.SUCCESS('Pre-load data deletion completed.'))

        # Only need mappings for Client and Staff since they already exist
        self.client_mapping = {}
        self.staff_mapping = {}
        self.purchase_order_line_mapping = {}
        self.stock_mapping = {}
        
        # Store JobFile instances to create dummy files later
        self.job_files_to_create = []
        
        # Store Job pricing updates for after JobPricing is created
        self.job_pricing_updates = []
        
        # Store JobPricing default_part updates for after JobPart is created
        self.jobpricing_defaultpart_updates = []

        with transaction.atomic():
            # Create random mappings for existing Client and Staff
            self._create_client_staff_mappings(backup_data)
            
            # Load all data, preserving original UUIDs
            self._load_data(backup_data)
            
            # Create dummy files at the end
            self._create_dummy_job_files()

        self.stdout.write(self.style.SUCCESS('Data restoration completed successfully.'))

    def _create_client_staff_mappings(self, backup_data):
        """
        Creates random mappings for Client and Staff IDs from production to existing development IDs.
        """
        self.stdout.write(self.style.MIGRATE_HEADING('Creating random mappings for Client and Staff...'))

        ClientModel = apps.get_model('client', 'Client')
        StaffModel = apps.get_model('accounts', 'Staff')

        # Get all existing Client and Staff IDs in the development database
        existing_client_ids = list(ClientModel.objects.values_list('id', flat=True))
        existing_staff_ids = list(StaffModel.objects.values_list('id', flat=True))

        # Collect all unique Client and Staff references
        old_client_ids = set()
        old_staff_emails = set()
        old_purchase_order_line_ids = set()
        old_stock_ids = set()

        for model_label in LOAD_ORDER:
            if model_label not in backup_data:
                continue
                
            for item in backup_data[model_label]:
                fields = item['fields']
                
                # Collect Client IDs
                if 'client' in fields and fields['client'] is not None:
                    old_client_ids.add(fields['client'])
                
                # Collect Staff emails from various fields
                if 'created_by' in fields and fields['created_by'] is not None:
                    old_staff_emails.add(fields['created_by'][0])
                
                # TimeEntry specific staff field
                if model_label == 'timesheet.timeentry' and 'staff' in fields and fields['staff'] is not None:
                    old_staff_emails.add(fields['staff'][0])
                
                # TimeEntry user field (if it exists as an alternative to staff)
                if model_label == 'timesheet.timeentry' and 'user' in fields and fields['user'] is not None:
                    if isinstance(fields['user'], list):
                        old_staff_emails.add(fields['user'][0])
                    else:
                        # If it's just an ID, we'll need to handle this differently
                        pass
                    
                if model_label == 'job.job' and 'people' in fields:
                    for email_list in fields['people']:
                        old_staff_emails.add(email_list[0])
                
                # JobEvent staff field
                if model_label == 'job.jobevent' and 'staff' in fields and fields['staff'] is not None:
                    old_staff_emails.add(fields['staff'][0])
                
                # Collect PurchaseOrderLine IDs
                if model_label == 'job.materialentry' and 'purchase_order_line' in fields and fields['purchase_order_line'] is not None:
                    old_purchase_order_line_ids.add(fields['purchase_order_line'])
                
                # Collect Stock IDs
                if model_label == 'job.materialentry' and 'source_stock' in fields and fields['source_stock'] is not None:
                    old_stock_ids.add(fields['source_stock'])

        # Create random mappings
        self.stdout.write(f"Creating random mappings for {len(old_client_ids)} clients...")
        for old_client_id in old_client_ids:
            self.client_mapping[old_client_id] = random.choice(existing_client_ids)

        self.stdout.write(f"Creating random mappings for {len(old_staff_emails)} staff...")
        for old_staff_email in old_staff_emails:
            self.staff_mapping[old_staff_email] = random.choice(existing_staff_ids)

        # Create random mappings for PurchaseOrderLines if they exist in dev
        if old_purchase_order_line_ids:
            try:
                PurchaseOrderLineModel = apps.get_model('purchasing', 'PurchaseOrderLine')
                existing_pol_ids = list(PurchaseOrderLineModel.objects.values_list('id', flat=True))
                
                if existing_pol_ids:
                    self.stdout.write(f"Creating random mappings for {len(old_purchase_order_line_ids)} purchase order lines...")
                    for old_pol_id in old_purchase_order_line_ids:
                        self.purchase_order_line_mapping[old_pol_id] = random.choice(existing_pol_ids)
                else:
                    self.stdout.write("No existing PurchaseOrderLines in dev - will set to None")
            except LookupError:
                self.stdout.write("PurchaseOrderLine model not found - will set to None")
        
        # Create random mappings for Stock if they exist in dev
        if old_stock_ids:
            try:
                StockModel = apps.get_model('purchasing', 'Stock')
                existing_stock_ids = list(StockModel.objects.values_list('id', flat=True))
                
                if existing_stock_ids:
                    self.stdout.write(f"Creating random mappings for {len(old_stock_ids)} stock items...")
                    for old_stock_id in old_stock_ids:
                        self.stock_mapping[old_stock_id] = random.choice(existing_stock_ids)
                else:
                    self.stdout.write("No existing Stock in dev - will set to None")
            except LookupError:
                self.stdout.write("Stock model not found - will set to None")

        self.stdout.write(self.style.SUCCESS('Random mappings created.'))

    def _load_data(self, backup_data):
        """
        Loads data from the backup, preserving original UUIDs.
        """
        self.stdout.write(self.style.MIGRATE_HEADING('Loading data into development environment...'))

        ClientModel = apps.get_model('client', 'Client')
        StaffModel = apps.get_model('accounts', 'Staff')

        for model_label in LOAD_ORDER:
            if model_label in EXCLUDE_MODELS or model_label not in backup_data:
                continue

            app_label, model_name = model_label.split('.')
            model = apps.get_model(app_label, model_name)
            
            model_data = backup_data[model_label]
            self.stdout.write(self.style.MIGRATE_HEADING(f"Creating {model_label} ({len(model_data)} records)"))
            
            for item in model_data:
                old_id = item['pk']
                fields = item['fields']

                # Handle M2M fields separately
                m2m_data = {}
                if model_label == 'job.job' and 'people' in fields:
                    m2m_data['people'] = fields.pop('people')

                # Replace Client foreign keys with mapped values
                if 'client' in fields and fields['client'] is not None:
                    fields['client'] = ClientModel.objects.get(pk=self.client_mapping[fields['client']])

                # Replace Staff foreign keys with mapped values
                if 'created_by' in fields and fields['created_by'] is not None:
                    old_staff_email = fields['created_by'][0]
                    fields['created_by'] = StaffModel.objects.get(pk=self.staff_mapping[old_staff_email])
                
                # Handle Staff FK in JobEvent
                if model_label == 'job.jobevent' and 'staff' in fields and fields['staff'] is not None:
                    old_staff_email = fields['staff'][0]
                    fields['staff'] = StaffModel.objects.get(pk=self.staff_mapping[old_staff_email])
                
                # Handle Staff FK in TimeEntry - this is the critical fix
                if model_label == 'timesheet.timeentry':
                    # Handle staff field
                    if 'staff' in fields and fields['staff'] is not None:
                        old_staff_email = fields['staff'][0]
                        fields['staff'] = StaffModel.objects.get(pk=self.staff_mapping[old_staff_email])
                    
                    # Handle user field (alternative to staff in some TimeEntry models)
                    if 'user' in fields and fields['user'] is not None:
                        if isinstance(fields['user'], list):
                            old_staff_email = fields['user'][0]
                            fields['user'] = StaffModel.objects.get(pk=self.staff_mapping[old_staff_email])
                        # If it's an ID reference, we might need to map it differently
                        elif isinstance(fields['user'], (int, str)):
                            # This would need adjustment based on your actual data format
                            # For now, assign a random staff member
                            fields['user'] = StaffModel.objects.get(pk=random.choice(list(StaffModel.objects.values_list('id', flat=True))))
                
                # Handle Job FK in JobPricing
                if model_label == 'job.jobpricing' and 'job' in fields:
                    job_model = apps.get_model('job', 'Job')
                    fields['job'] = job_model.objects.get(pk=fields['job'])
                    
                    # Defer default_part FK until JobPart records exist
                    if 'default_part' in fields and fields['default_part'] is not None:
                        self.jobpricing_defaultpart_updates.append({
                            'jobpricing_id': old_id,
                            'default_part_id': fields.pop('default_part')
                        })
                
                # Handle Job FK in other models (but not JobPart which uses job_pricing)
                if model_label in ['job.jobfile', 'job.jobevent', 'timesheet.timeentry'] and 'job' in fields:
                    job_model = apps.get_model('job', 'Job')
                    fields['job'] = job_model.objects.get(pk=fields['job'])
                
                # Handle JobPricing FK in JobPart
                if model_label == 'job.jobpart' and 'job_pricing' in fields:
                    jobpricing_model = apps.get_model('job', 'JobPricing')
                    fields['job_pricing'] = jobpricing_model.objects.get(pk=fields['job_pricing'])
                
                # Handle JobPart FK in models that use it
                if 'job_part' in fields and fields['job_part'] is not None:
                    jobpart_model = apps.get_model('job', 'JobPart')
                    fields['job_part'] = jobpart_model.objects.get(pk=fields['job_part'])
                
                # Handle JobPricing FK in MaterialEntry, AdjustmentEntry, JobEvent, TimeEntry
                if model_label in ['job.materialentry', 'job.adjustmententry', 'job.jobevent', 'timesheet.timeentry'] and 'job_pricing' in fields and fields['job_pricing'] is not None:
                    jobpricing_model = apps.get_model('job', 'JobPricing')
                    fields['job_pricing'] = jobpricing_model.objects.get(pk=fields['job_pricing'])
                
                # Handle PurchaseOrderLine FK in MaterialEntry
                if model_label == 'job.materialentry' and 'purchase_order_line' in fields and fields['purchase_order_line'] is not None:
                    if fields['purchase_order_line'] in self.purchase_order_line_mapping:
                        try:
                            pol_model = apps.get_model('purchasing', 'PurchaseOrderLine')
                            fields['purchase_order_line'] = pol_model.objects.get(pk=self.purchase_order_line_mapping[fields['purchase_order_line']])
                        except LookupError:
                            fields['purchase_order_line'] = None
                    else:
                        # No POLs exist in dev, set to None
                        fields['purchase_order_line'] = None
                
                # Handle Stock FK in MaterialEntry
                if model_label == 'job.materialentry' and 'source_stock' in fields and fields['source_stock'] is not None:
                    if fields['source_stock'] in self.stock_mapping:
                        try:
                            stock_model = apps.get_model('purchasing', 'Stock')
                            fields['source_stock'] = stock_model.objects.get(pk=self.stock_mapping[fields['source_stock']])
                        except LookupError:
                            fields['source_stock'] = None
                    else:
                        # No Stock exists in dev, set to None
                        fields['source_stock'] = None
                
                # Handle SupplierPriceList FK in SupplierProduct
                if 'supplier_price_list' in fields and fields['supplier_price_list'] is not None:
                    pricelist_model = apps.get_model('quoting', 'SupplierPriceList')
                    fields['supplier_price_list'] = pricelist_model.objects.get(pk=fields['supplier_price_list'])

                # Handle JobFile file paths
                if model_label == 'job.jobfile' and 'file' in fields and fields['file']:
                    self.job_files_to_create.append({
                        'old_id': old_id,
                        'original_path': fields['file']
                    })
                    fields['file'] = ''

                # For Job model, defer pricing fields until JobPricing records exist
                if model_label == 'job.job':
                    pricing_update = {'job_id': old_id}
                    for field in ['latest_estimate_pricing', 'latest_quote_pricing', 'latest_reality_pricing']:
                        if field in fields:
                            pricing_update[field] = fields.pop(field)
                    if 'archived_pricings' in fields:
                        pricing_update['archived_pricings'] = fields.pop('archived_pricings')
                    
                    if len(pricing_update) > 1:  # Has more than just job_id
                        self.job_pricing_updates.append(pricing_update)

                # Create with original UUID
                try:
                    new_instance = model.objects.create(pk=old_id, **fields)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error creating {model_label} with ID {old_id}: {e}"))
                    self.stdout.write(f"Fields: {fields}")
                    raise

                # Handle M2M relationships
                if m2m_data.get('people'):
                    staff_to_add = []
                    for email_list in m2m_data['people']:
                        staff_email = email_list[0]
                        staff = StaffModel.objects.get(pk=self.staff_mapping[staff_email])
                        staff_to_add.append(staff)
                    new_instance.people.set(staff_to_add)

                self.stdout.write(f"  Created {model_label}: {old_id}")
            
            self.stdout.write(self.style.SUCCESS(f"Completed {model_label}: {len(model_data)} records"))
        
        # Apply deferred Job pricing updates
        self._update_job_pricing_fields()
        
        # Apply deferred JobPricing default_part updates
        self._update_jobpricing_defaultpart_fields()
        
        # Fix special jobs to be shop jobs
        self._fix_special_jobs_as_shop_jobs()
        
        # Validate shop client setup
        self._validate_shop_client_setup()

    def _create_dummy_job_files(self):
        """
        Creates dummy physical files for JobFile instances.
        """
        if not self.job_files_to_create:
            return
            
        self.stdout.write(self.style.MIGRATE_HEADING('Creating dummy physical files for JobFile instances...'))

        for job_file_info in self.job_files_to_create:
            original_path = job_file_info['original_path']
            old_id = job_file_info['old_id']

            relative_path = original_path.lstrip('/')
            dummy_file_path = os.path.join(settings.MEDIA_ROOT, relative_path)

            os.makedirs(os.path.dirname(dummy_file_path), exist_ok=True)

            with open(dummy_file_path, 'w') as f:
                f.write(f"This is a dummy file for JobFile with original path: {original_path}\n")
                f.write(f"Restored from old ID: {old_id}\n")
            self.stdout.write(f"Created dummy file: {dummy_file_path}")

    def _update_job_pricing_fields(self):
        """
        Updates Job instances with their pricing foreign keys after JobPricing records are created.
        This mimics the normal Job creation pattern:
        1. Create Job without pricing fields
        2. Create JobPricing records
        3. Update Job with pricing FKs and save again
        """
        if not self.job_pricing_updates:
            return
            
        self.stdout.write(self.style.MIGRATE_HEADING('Updating Job pricing fields...'))
        
        JobModel = apps.get_model('job', 'Job')
        
        for update in self.job_pricing_updates:
            job = JobModel.objects.get(pk=update['job_id'])
            
            # Update single pricing fields
            for field in ['latest_estimate_pricing', 'latest_quote_pricing', 'latest_reality_pricing']:
                if field in update:
                    setattr(job, field + '_id', update[field])
            
            # Update archived_pricings list (many-to-many field)
            if 'archived_pricings' in update:
                # Convert list of UUIDs to JobPricing instances
                JobPricingModel = apps.get_model('job', 'JobPricing')
                pricing_instances = []
                for pricing_id in update['archived_pricings']:
                    try:
                        pricing = JobPricingModel.objects.get(pk=pricing_id)
                        pricing_instances.append(pricing)
                    except JobPricingModel.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Warning: JobPricing {pricing_id} not found for archived_pricings"))
                job.archived_pricings.set(pricing_instances)
            
            job.save()
        
        self.stdout.write(self.style.SUCCESS(f'Updated pricing fields on {len(self.job_pricing_updates)} jobs.'))

    def _update_jobpricing_defaultpart_fields(self):
        """
        Updates JobPricing instances with their default_part foreign key after JobPart records are created.
        """
        if not self.jobpricing_defaultpart_updates:
            return
            
        self.stdout.write(self.style.MIGRATE_HEADING('Updating JobPricing default_part fields...'))
        
        JobPricingModel = apps.get_model('job', 'JobPricing')
        JobPartModel = apps.get_model('job', 'JobPart')
        
        for update in self.jobpricing_defaultpart_updates:
            jobpricing = JobPricingModel.objects.get(pk=update['jobpricing_id'])
            jobpart = JobPartModel.objects.get(pk=update['default_part_id'])
            jobpricing.default_part = jobpart
            jobpricing.save()
        
        self.stdout.write(self.style.SUCCESS(f'Updated default_part fields on {len(self.jobpricing_defaultpart_updates)} JobPricing records.'))

    def _fix_special_jobs_as_shop_jobs(self):
        """
        Updates all jobs with status 'special' to have the shop job client_id.
        This ensures proper shop hour calculations in KPI reports.
        """
        self.stdout.write(self.style.MIGRATE_HEADING('Fixing special jobs to be shop jobs...'))
        
        JobModel = apps.get_model('job', 'Job')
        ClientModel = apps.get_model('client', 'Client')
        
        shop_job_client_id = "00000000-0000-0000-0000-000000000001"
        
        # First, ensure the shop client exists
        shop_client, created = ClientModel.objects.get_or_create(
            id=shop_job_client_id,
            defaults={
                'name': 'Morris Sheetmetal (Shop)',
                'primary_contact_email': 'shop@morrissheetmetal.co.nz',
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('Created shop client'))
        
        # Update all special jobs to use the shop client
        special_jobs = JobModel.objects.filter(status='special')
        count = special_jobs.update(client=shop_client)
        
        self.stdout.write(self.style.SUCCESS(f'Updated {count} special jobs to be shop jobs'))

    def _validate_shop_client_setup(self):
        """
        Validates that a shop client exists and has a valid Xero contact ID.
        Fails the restore process if not properly configured.
        """
        self.stdout.write(self.style.MIGRATE_HEADING('Validating shop client setup...'))
        
        ClientModel = apps.get_model('client', 'Client')
        
        try:
            # Look for a client ending with " Shop" that has a Xero contact ID
            shop_client = ClientModel.objects.filter(
                name__endswith=' Shop',
                xero_contact_id__isnull=False
            ).first()
            
            if not shop_client:
                raise CommandError(
                    "CRITICAL: No shop client found with valid Xero contact ID!\n"
                    "You must:\n"
                    "1. Create 'Demo Company Shop' contact in Xero\n"
                    "2. Run 'python manage.py setup_dev_xero' to sync and configure shop client\n"
                    "3. Then re-run this restore command"
                )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Shop client validated: {shop_client.name} "
                    f"(ID: {shop_client.id}, Xero ID: {shop_client.xero_contact_id})"
                )
            )
            
            # Also validate that special jobs are using the shop client
            JobModel = apps.get_model('job', 'Job')
            special_jobs_count = JobModel.objects.filter(status='special').count()
            shop_jobs_count = JobModel.objects.filter(
                status='special',
                client_id=shop_client.id
            ).count()
            
            if special_jobs_count != shop_jobs_count:
                self.stdout.write(
                    self.style.WARNING(
                        f"Warning: {special_jobs_count - shop_jobs_count} special jobs "
                        f"are not assigned to the shop client"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ All {special_jobs_count} special jobs are correctly assigned to shop client"
                    )
                )
                
        except Exception as e:
            raise CommandError(f"Shop client validation failed: {str(e)}")