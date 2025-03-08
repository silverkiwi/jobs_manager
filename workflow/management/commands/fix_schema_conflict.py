from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

class Command(BaseCommand):
    help = 'Fix schema conflicts between model and database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check', 
            action='store_true', 
            help='Only check database and model status'
        )
        parser.add_argument(
            '--add-column', 
            action='store_true', 
            help='Add password_needs_reset column to database'
        )
        parser.add_argument(
            '--clean-migrations', 
            action='store_true', 
            help='Clean problematic migrations'
        )

    def handle(self, *args, **options):
        # Check if column exists
        column_exists = self._check_column_exists()
        
        if options['check']:
            if column_exists:
                self.stdout.write(self.style.SUCCESS('The password_needs_reset column EXISTS in the database.'))
            else:
                self.stdout.write(self.style.WARNING('The password_needs_reset column does NOT exist in the database.'))
            
            # Check for problematic migrations
            self._check_problematic_migrations()
            return
        
        # Clean problematic migrations
        if options['clean_migrations']:
            self._clean_problematic_migrations()
            self.stdout.write(self.style.SUCCESS('Problematic migrations removed successfully!'))
            return
        
        # Add column if needed
        if options['add_column'] and not column_exists:
            self._add_column()
            self.stdout.write(self.style.SUCCESS('Column password_needs_reset added successfully!'))
            return
        
        self.stdout.write(self.style.WARNING('No action specified. Use --check, --add-column or --clean-migrations.'))
    
    def _check_column_exists(self):
        with connection.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM workflow_staff LIKE 'password_needs_reset'")
            column_exists = bool(cursor.fetchone())
            return column_exists
    
    def _add_column(self):
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE workflow_staff ADD COLUMN password_needs_reset BOOLEAN DEFAULT FALSE")
    
    def _check_problematic_migrations(self):
        migrations = MigrationRecorder.Migration.objects.filter(
            app='workflow', 
            name__contains='password_needs_reset'
        )
        
        if migrations.exists():
            self.stdout.write(self.style.WARNING('Migrations related to password_needs_reset:'))
            for migration in migrations:
                self.stdout.write(f"  - {migration.app}.{migration.name}")
        else:
            self.stdout.write(self.style.SUCCESS('No migrations related to password_needs_reset.'))
    
    def _clean_problematic_migrations(self):
        migrations = MigrationRecorder.Migration.objects.filter(
            app='workflow', 
            name__contains='password_needs_reset'
        )
        
        if migrations.exists():
            self.stdout.write(self.style.WARNING('Removing migrations:'))
            for migration in migrations:
                self.stdout.write(f"  - {migration.app}.{migration.name}")
                migration.delete()
        else:
            self.stdout.write(self.style.SUCCESS('No problematic migrations to remove.'))
