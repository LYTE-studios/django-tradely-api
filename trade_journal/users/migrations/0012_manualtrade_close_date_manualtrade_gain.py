# Generated by Django 5.1.4 on 2024-12-30 11:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_manualtrade_duration_in_minutes'),
    ]

    operations = [
        migrations.AddField(
            model_name='manualtrade',
            name='close_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='manualtrade',
            name='gain',
            field=models.FloatField(blank=True, default=0.0, null=True),
        ),
    ]
