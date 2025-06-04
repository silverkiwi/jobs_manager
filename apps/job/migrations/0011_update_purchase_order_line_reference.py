# apps/job/migrations/0011_update_purchase_order_line_reference.py
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ("job", "0010_populate_priority_for_existing_jobs"),
        ("purchasing", "0002_move_purchase_models_database"),  # Ensure purchasing models exist
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='materialentry',
                    name='purchase_order_line',
                    field=models.ForeignKey(
                        blank=True,
                        help_text='Convenience link to original PO line (derived via source_stock)',
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='material_entries',
                        to='purchasing.purchaseorderline'  # Updated reference
                    ),
                ),
            ],
            database_operations=[
                # No database operations needed - tables are already correct
            ],
        ),
    ]