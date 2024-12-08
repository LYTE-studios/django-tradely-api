# Generated by Django 5.1.4 on 2024-12-09 10:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metatrade', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Trade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(max_length=255)),
                ('trade_id', models.CharField(max_length=255)),
                ('symbol', models.CharField(max_length=10)),
                ('volume', models.FloatField()),
                ('price_open', models.FloatField()),
                ('price_close', models.FloatField()),
                ('profit', models.FloatField()),
                ('create_time', models.DateTimeField()),
                ('close_time', models.DateTimeField()),
            ],
        ),
    ]
