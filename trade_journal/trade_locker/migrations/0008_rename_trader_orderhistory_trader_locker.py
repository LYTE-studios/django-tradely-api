# Generated by Django 5.1.4 on 2024-12-11 06:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('trade_locker', '0007_remove_orderhistory_history_orderhistory_amount_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='orderhistory',
            old_name='trader',
            new_name='trader_locker',
        ),
    ]
