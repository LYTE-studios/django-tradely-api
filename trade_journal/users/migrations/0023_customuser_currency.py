# Generated by Django 5.1.4 on 2025-01-23 17:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0022_alter_manualtrade_gain"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="currency",
            field=models.CharField(default="USD", max_length=10, null=True),
        ),
    ]
