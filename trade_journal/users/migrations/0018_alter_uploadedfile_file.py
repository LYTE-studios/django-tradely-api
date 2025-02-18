# Generated by Django 5.1.4 on 2025-01-19 20:58

import users.models
import users.storage_backend
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0017_tradeaccount_credentials"),
    ]

    operations = [
        migrations.AlterField(
            model_name="uploadedfile",
            name="file",
            field=models.ImageField(
                blank=True,
                null=True,
                storage=users.storage_backend.MediaStorage(),
                upload_to=users.models.UploadedFile.upload_location,
            ),
        ),
    ]
