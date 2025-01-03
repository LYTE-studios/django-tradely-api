# Generated by Django 5.1.4 on 2024-12-11 06:21

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trade_locker', '0006_alter_traderlockeraccount_key_code'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='orderhistory',
            name='history',
        ),
        migrations.AddField(
            model_name='orderhistory',
            name='amount',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='orderhistory',
            name='instrument_id',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='orderhistory',
            name='market',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='orderhistory',
            name='market_status',
            field=models.CharField(default='market', max_length=255),
        ),
        migrations.AddField(
            model_name='orderhistory',
            name='order_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='orderhistory',
            name='position_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='orderhistory',
            name='price',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='orderhistory',
            name='side',
            field=models.CharField(default='buy', max_length=10),
        ),
        migrations.AddField(
            model_name='orderhistory',
            name='trader',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='trade_locker.traderlockeraccount'),
        ),
    ]
