import datetime
from django.core.management.base import BaseCommand
from django.db import connection, transaction


class Command(BaseCommand):
    help = 'Fixes migration order by updating timestamps to resolve dependency inconsistencies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation and execute immediately'
        )
        parser.add_argument(
            '--parent',
            type=str,
            help='Specify parent migration (format: app.migration_name)',
        )
        parser.add_argument(
            '--child',
            type=str,
            help='Specify child migration (format: app.migration_name)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Running in dry-run mode - no changes will be made'))
        
        # Default specific migrations if not provided
        parent_migration = options.get('parent') or 'job.0009_alter_jobpart_options_and_more' 
        child_migration = options.get('child') or 'workflow.0151_remove_purchaseline_purchase_and_more'
        
        # Split into app and name
        parent_app, parent_name = parent_migration.split('.')
        child_app, child_name = child_migration.split('.')
        
        # Check migrations exist in database
        with connection.cursor() as cursor:
            # Check parent migration
            cursor.execute(
                "SELECT app, name, applied FROM django_migrations WHERE app = %s AND name = %s",
                [parent_app, parent_name]
            )
            parent_record = cursor.fetchone()
            
            if not parent_record:
                self.stdout.write(self.style.ERROR(
                    f"Parent migration {parent_migration} not found in database!"
                ))
                return
                
            # Check child migration
            cursor.execute(
                "SELECT app, name, applied FROM django_migrations WHERE app = %s AND name = %s",
                [child_app, child_name]
            )
            child_record = cursor.fetchone()
            
            if not child_record:
                self.stdout.write(self.style.ERROR(
                    f"Child migration {child_migration} not found in database!"
                ))
                return
            
            parent_applied = parent_record[2]  # the 'applied' field
            child_applied = child_record[2]
            
            # Check if there's already a problem
            if child_applied <= parent_applied:
                self.stdout.write(self.style.WARNING(
                    f"Inconsistency detected! Child {child_migration} ({child_applied}) "
                    f"is applied before parent {parent_migration} ({parent_applied})"
                ))
                
                # Calculate new timestamps
                # Make parent 5 minutes before child
                new_child_timestamp = parent_applied + datetime.timedelta(minutes=5)
                
                self.stdout.write(self.style.WARNING(
                    f"Will update {child_migration} timestamp to: {new_child_timestamp}"
                ))
                
                # Ask for confirmation
                if not force and not dry_run:
                    confirm = input('Do you want to proceed with these changes? [y/N]: ')
                    if confirm.lower() != 'y':
                        self.stdout.write(self.style.WARNING('Operation cancelled'))
                        return
                
                # Apply changes
                if not dry_run:
                    try:
                        with transaction.atomic():
                            cursor.execute(
                                "UPDATE django_migrations SET applied = %s WHERE app = %s AND name = %s",
                                [new_child_timestamp, child_app, child_name]
                            )
                            self.stdout.write(self.style.SUCCESS(
                                f"Successfully updated {child_migration} timestamp to {new_child_timestamp}"
                            ))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error updating migration timestamps: {str(e)}"))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"No inconsistency found! Child {child_migration} ({child_applied}) "
                    f"is already applied after parent {parent_migration} ({parent_applied})"
                ))
                