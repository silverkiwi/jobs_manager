from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Drops all tables and recreates the database"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            cursor.execute("PRAGMA foreign_keys = OFF;")
            for table in tables:
                try:
                    cursor.execute(f"DROP TABLE IF EXISTS {table[0]};")
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"Failed to drop table {table[0]}: {e}")
                    )
            cursor.execute("PRAGMA foreign_keys = ON;")

        self.stdout.write(self.style.SUCCESS("Successfully dropped all tables"))
        self.stdout.write(
            self.style.WARNING("You should run `python manage.py migrate` now")
        )
