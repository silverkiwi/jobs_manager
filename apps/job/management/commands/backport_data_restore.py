import os
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Post-restore fixes for dev environment'

    def handle(self, *args, **options):
        # Create dummy files for JobFile instances
        from apps.job.models import JobFile
        
        self.stdout.write('Creating dummy files for JobFile instances...')
        for job_file in JobFile.objects.filter(file_path__isnull=False).exclude(file_path=''):
            dummy_path = os.path.join(settings.MEDIA_ROOT, str(job_file.file_path))
            os.makedirs(os.path.dirname(dummy_path), exist_ok=True)
            with open(dummy_path, 'w') as f:
                f.write(f"Dummy file for JobFile {job_file.pk}\n")
                f.write(f"Original path: {job_file.file_path}\n")
            self.stdout.write(f"Created dummy file: {dummy_path}")
                    
        # Create default admin if needed
        from apps.accounts.models import Staff
        
        self.stdout.write('Creating default admin user...')
        admin_user, created = Staff.objects.get_or_create(
            email='defaultadmin@example.com',
            defaults={
                'first_name': 'Default',
                'last_name': 'Admin',
                'preferred_name': None,
                'wage_rate': '40.00',
                'hours_mon': '8.0',
                'hours_tue': '8.0',
                'hours_wed': '8.0',
                'hours_thu': '8.0',
                'hours_fri': '8.0',
                'hours_sat': '0.00',
                'hours_sun': '0.00',
                'ims_payroll_id': 'ADMIN-DEV',
                'is_active': True,
                'is_staff': True,
                'is_superuser': True,
                'password': 'pbkdf2_sha256$870000$5Nw3RUuFaZZPCkeyVOm4kx$Attep1SqGF6ymdwm44LOte4wwszqte0W5ey3xcENFAI=',
                'date_joined': '2024-01-01T00:00:00Z',
                'created_at': '2024-01-01T00:00:00Z',
                'updated_at': '2024-01-01T00:00:00Z'
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('Created defaultadmin@example.com user'))
        else:
            self.stdout.write(self.style.SUCCESS('defaultadmin@example.com user already exists'))
        
        self.stdout.write(self.style.SUCCESS('Post-restore fixes completed'))