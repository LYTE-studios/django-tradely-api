# Generated by Django 5.1.4 on 2024-12-13 13:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_merge_0002_customuser_date_of_birth_0003_tradenote'),
    ]

    operations = [
        migrations.AddField(
            model_name='manualtrade',
            name='profit',
            field=models.FloatField(blank=True, default=0.0, null=True),
        ),
    ]
