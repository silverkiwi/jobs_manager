import sys
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Executes emergency fixes for database schema issues'

    def handle(self, *args, **options):
        self.stdout.write("Starting emergency database fix...")
        
        # 1. Check if password_needs_reset column exists
        with connection.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM workflow_staff LIKE 'password_needs_reset'")
            column_exists = bool(cursor.fetchone())
        
        if column_exists:
            self.stdout.write(self.style.SUCCESS(
                "Column 'password_needs_reset' already exists. No action needed."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "Column 'password_needs_reset' doesn't exist. Adding it..."
            ))
            
            try:
                # 2. Add column if it doesn't exist
                with connection.cursor() as cursor:
                    cursor.execute(
                        "ALTER TABLE workflow_staff ADD COLUMN password_needs_reset BOOLEAN DEFAULT FALSE"
                    )
                self.stdout.write(self.style.SUCCESS(
                    "Column added successfully!"
                ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"Error adding column: {e}"
                ))
                return
        
        # 3. Clean problematic migrations
        self.stdout.write("Checking problematic migrations...")
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, app, name FROM django_migrations WHERE app='workflow' AND name LIKE '%password_needs_reset%'"
                )
                migrations = cursor.fetchall()
                
                if migrations:
                    self.stdout.write(self.style.WARNING(f"Found {len(migrations)} problematic migrations:"))
                    for migration in migrations:
                        self.stdout.write(f"  - ID: {migration[0]}, App: {migration[1]}, Name: {migration[2]}")
                    
                    confirm = input("Do you want to remove these migrations? (y/n): ")
                    if confirm.lower() == 'y':
                        with connection.cursor() as cursor:
                            cursor.execute(
                                "DELETE FROM django_migrations WHERE app='workflow' AND name LIKE '%password_needs_reset%'"
                            )
                        self.stdout.write(self.style.SUCCESS("Migrations removed successfully!"))
                else:
                    self.stdout.write("No problematic migrations found.")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error checking migrations: {e}"))
        
        # 4. Final recommendations
        self.stdout.write("\nEmergency fix completed!")
        self.stdout.write(self.style.WARNING(
            "\nAttention: This was an emergency fix. For a permanent solution:"
        ))
        self.stdout.write("1. Run 'python manage.py makemigrations' to create a new migration")
        self.stdout.write("2. Edit the generated migration to include only the migrations.AddField operation")
        self.stdout.write("3. Run 'python manage.py migrate --fake workflow' to update the migrations state")