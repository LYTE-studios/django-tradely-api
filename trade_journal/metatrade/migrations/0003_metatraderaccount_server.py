# Generated by Django 5.1.4 on 2024-12-09 11:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metatrade', '0002_trade'),
    ]

    operations = [
        migrations.AddField(
            model_name='metatraderaccount',
            name='server',
            field=models.CharField(blank=True, max_length=255, null=None),
        ),
    ]