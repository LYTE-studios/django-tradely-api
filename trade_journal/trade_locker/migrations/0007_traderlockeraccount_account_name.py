# Generated by Django 5.1.4 on 2024-12-10 18:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trade_locker', '0006_alter_traderlockeraccount_key_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='traderlockeraccount',
            name='account_name',
            field=models.CharField(default='-', max_length=255),
            preserve_default=False,
        ),
    ]
