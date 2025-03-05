from django.db import migrations

def cleanup_company_defaults(apps, schema_editor):
    """
    Ensure only one CompanyDefaults record exists.
    Keep the first record and delete any others.
    """
    CompanyDefaults = apps.get_model('workflow', 'CompanyDefaults')
    
    # Get all records
    records = list(CompanyDefaults.objects.all())
    
    if records:
        # Keep the first record
        keep_record = records[0]
        
        # Delete any other records
        CompanyDefaults.objects.exclude(pk=keep_record.pk).delete()
    else:
        # Create a record if none exist
        CompanyDefaults.objects.create()

class Migration(migrations.Migration):
    dependencies = [
        ('workflow', '0083_setup_xero_sync_service'),
    ]

    operations = [
        # Run the cleanup function
        migrations.RunPython(
            cleanup_company_defaults,
            reverse_code=migrations.RunPython.noop
        ),
    ] 