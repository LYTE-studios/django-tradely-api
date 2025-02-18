# Generated by Django 5.1.4 on 2025-01-09 08:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ctrader", "0004_alter_ctraderaccount_account_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="ctrade",
            name="close_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="ctrade",
            name="is_deposit",
            field=models.BooleanField(default=False),
        ),
    ]
