# Generated by Django 5.1.4 on 2024-12-27 16:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0010_alter_manualtrade_account"),
    ]

    operations = [
        migrations.AddField(
            model_name="manualtrade",
            name="duration_in_minutes",
            field=models.FloatField(blank=True, default=0, null=True),
        ),
    ]
