# Generated by Django 5.1.4 on 2025-01-09 08:38

import users.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0013_uploadedfile"),
    ]

    operations = [
        migrations.AlterField(
            model_name="uploadedfile",
            name="file",
            field=models.FileField(upload_to=users.models.UploadedFile.upload_location),
        ),
    ]
