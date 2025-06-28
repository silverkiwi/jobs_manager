from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("purchasing", "0007_stock_unique_xero_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaseorderline",
            name="item_code",
            field=models.CharField(
                max_length=50,
                null=True,
                blank=True,
                db_index=True,
                help_text="Internal item code for Xero integration",
            ),
        ),
    ]
