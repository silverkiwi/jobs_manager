import datetime
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder


class Command(BaseCommand):
    help = 'Fixes the order of migrations in django_migrations table by adjusting timestamps'

    def handle(self, *args, **options):
        self.stdout.write('Loading migration graph...')
        
        # Load the migration graph
        loader = MigrationLoader(connection)
        graph = loader.graph
        recorder = MigrationRecorder(connection)
        
        # Get all applied migrations
        applied_migrations = recorder.applied_migrations()
        
        # Map of (app_label, migration_name) to Migration object
        migration_dict = {}
        
        # Build lookup dictionary from recorder data
        with connection.cursor() as cursor:
            cursor.execute("SELECT app, name, applied FROM django_migrations ORDER BY applied")
            rows = cursor.fetchall()
            for app, name, applied in rows:
                migration_dict[(app, name)] = {
                    'applied': applied,
                    'key': (app, name)
                }
        
        self.stdout.write(f'Found {len(migration_dict)} applied migrations')
        
        # Identify inconsistencies
        inconsistencies = []
        for app_label, migration_name in migration_dict.keys():
            if (app_label, migration_name) not in graph.nodes:
                self.stdout.write(self.style.WARNING(
                    f"Migration {app_label}.{migration_name} exists in database but not in files. Skipping."
                ))
                continue
                
            node = graph.node_map[(app_label, migration_name)]
            
            # Check each dependency
            for parent in graph.dependencies.get((app_label, migration_name), []):
                parent_app, parent_name = parent
                
                # Skip if the parent migration is not applied yet
                if (parent_app, parent_name) not in migration_dict:
                    continue
                
                # Compare timestamps - dependency should be applied before
                if migration_dict[(app_label, migration_name)]['applied'] <= migration_dict[(parent_app, parent_name)]['applied']:
                    inconsistencies.append({
                        'child': (app_label, migration_name),
                        'parent': (parent_app, parent_name),
                    })
        
        if not inconsistencies:
            self.stdout.write(self.style.SUCCESS('No inconsistencies found!'))
            return
            
        self.stdout.write(f'Found {len(inconsistencies)} inconsistencies to fix')
        
        # Fix inconsistencies
        with transaction.atomic():
            # Sort the graph to get correct order
            sorted_nodes = list(graph.forwards_plan(graph.leaf_nodes()))
            
            # Apply a time offset to each migration based on its position in the sorted graph
            base_time = datetime.datetime.now() - datetime.timedelta(days=1)
            time_increment = datetime.timedelta(seconds=10)
            
            # Create mapping of node to new timestamp
            new_timestamps = {}
            for i, node_key in enumerate(sorted_nodes):
                if node_key in migration_dict:
                    new_timestamps[node_key] = base_time + (time_increment * i)
            
            # Apply new timestamps
            with connection.cursor() as cursor:
                for node_key, timestamp in new_timestamps.items():
                    app, name = node_key
                    cursor.execute(
                        "UPDATE django_migrations SET applied = %s WHERE app = %s AND name = %s",
                        [timestamp, app, name]
                    )
                    self.stdout.write(f"Updated {app}.{name} timestamp to {timestamp}")
            
            self.stdout.write(self.style.SUCCESS('Migration timestamps updated successfully!'))
            