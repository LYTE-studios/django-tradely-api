# Generated by Django 5.1.4 on 2024-12-13 18:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_remove_manualtrade_notes_alter_manualtrade_quantity"),
    ]

    operations = [
        migrations.AlterField(
            model_name="manualtrade",
            name="price",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=15, null=True
            ),
        ),
        migrations.AlterField(
            model_name="manualtrade",
            name="symbol",
            field=models.CharField(default="", max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name="manualtrade",
            name="total_amount",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=15, null=True
            ),
        ),
        migrations.AlterField(
            model_name="manualtrade",
            name="trade_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
