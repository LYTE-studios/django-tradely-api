# Generated by Django 5.1.4 on 2025-01-23 17:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0023_customuser_currency'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExchangeRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('currency_in', models.CharField(max_length=10)),
                ('currency_out', models.CharField(max_length=10)),
                ('exchange_rate', models.DecimalField(decimal_places=10, max_digits=20)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
