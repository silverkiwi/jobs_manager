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
        parser.add_argument(
            '--list-migrations',
            type=str,
            help='List all migrations for a specific app',
        )

    def list_migrations(self, app_label):
        """Lists all migrations for a specific app and return them."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT app, name, applied FROM django_migrations WHERE app = %s ORDER BY applied",
                [app_label]
            )
            migrations = cursor.fetchall()
            
            if not migrations:
                self.stdout.write(self.style.ERROR(f"No migrations found for app '{app_label}'"))
                return []
                
            self.stdout.write(self.style.SUCCESS(f"Found {len(migrations)} migrations for app '{app_label}':"))
            for i, (app, name, applied) in enumerate(migrations, 1):
                self.stdout.write(f"{i}. {app}.{name} ({applied})")
                
            return migrations
    
    def find_migration_by_prefix(self, app_label, name_prefix):
        """Find a migration by name prefix (e.g., '0009_' will match '0009_something')."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT app, name, applied FROM django_migrations WHERE app = %s AND name LIKE %s ORDER BY applied",
                [app_label, f"{name_prefix}%"]
            )
            migrations = cursor.fetchall()
            
            if migrations:
                return migrations[0]  # Return the first match
            return None

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        # Check if we just want to list migrations
        if options.get('list_migrations'):
            self.list_migrations(options['list_migrations'])
            return
        
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
            
            # Try to find by prefix if exact match not found
            if not parent_record:
                # Extract prefix (e.g., "0009_" from "0009_alter_jobpart_options_and_more")
                prefix = parent_name.split('_')[0] + '_'
                self.stdout.write(self.style.WARNING(
                    f"Parent migration {parent_migration} not found, looking for alternatives with prefix '{prefix}'"
                ))
                
                parent_record = self.find_migration_by_prefix(parent_app, prefix)
                
                if parent_record:
                    self.stdout.write(self.style.SUCCESS(
                        f"Found alternative parent migration: {parent_record[0]}.{parent_record[1]}"
                    ))
                    parent_app, parent_name = parent_record[0], parent_record[1]
                    parent_migration = f"{parent_app}.{parent_name}"
                else:
                    # If still not found, show available migrations
                    self.stdout.write(self.style.ERROR(
                        f"Parent migration {parent_migration} not found! Showing available migrations:"
                    ))
                    self.list_migrations(parent_app)
                    return
                
            # Check child migration
            cursor.execute(
                "SELECT app, name, applied FROM django_migrations WHERE app = %s AND name = %s",
                [child_app, child_name]
            )
            child_record = cursor.fetchone()
            
            # Try to find by prefix if exact match not found
            if not child_record:
                prefix = child_name.split('_')[0] + '_'
                self.stdout.write(self.style.WARNING(
                    f"Child migration {child_migration} not found, looking for alternatives with prefix '{prefix}'"
                ))
                
                child_record = self.find_migration_by_prefix(child_app, prefix)
                
                if child_record:
                    self.stdout.write(self.style.SUCCESS(
                        f"Found alternative child migration: {child_record[0]}.{child_record[1]}"
                    ))
                    child_app, child_name = child_record[0], child_record[1]
                    child_migration = f"{child_app}.{child_name}"
                else:
                    self.stdout.write(self.style.ERROR(
                        f"Child migration {child_migration} not found! Showing available migrations:"
                    ))
                    self.list_migrations(child_app)
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
                # Make child 5 minutes after parent
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
                