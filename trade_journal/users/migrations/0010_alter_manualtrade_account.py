# Generated by Django 5.1.4 on 2024-12-17 18:37

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0009_remove_manualtrade_user_manualtrade_account"),
    ]

    operations = [
        migrations.AlterField(
            model_name="manualtrade",
            name="account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="manual_trades",
                to="users.tradeaccount",
            ),
        ),
    ]
