# Generated by Django 5.1.4 on 2024-12-09 10:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trade_locker', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instruments',
            name='country',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='instruments',
            name='logoUrl',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]