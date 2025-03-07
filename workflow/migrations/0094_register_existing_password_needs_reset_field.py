from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("workflow", "0093_remove_historicalstaff_password_needs_reset_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name='staff',
                    name='password_needs_reset',
                    field=models.BooleanField(default=False),
                ),
            ],
        ),
    ]