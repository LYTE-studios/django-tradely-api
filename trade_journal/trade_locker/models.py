# trade_locker/models.py

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class TraderLockerAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.EmailField(unique=True, null=True)
    password = models.TextField(null=True)
    key_code = models.BinaryField(null=True)
    refresh_token = models.CharField(max_length=1255)
    server = models.CharField(max_length=255)
    demo_status = models.BooleanField(default=True)  # demo mode status
    def __str__(self):
        return f"{self.user.username}'s Trade Locker Account"


class OrderHistory(models.Model):
    acc_id = models.CharField(max_length=255)
    history = models.TextField()


class Instruments(models.Model):
    tradableInstrumentId = models.IntegerField()
    name = models.CharField(max_length=255)
    description = models.TextField()
    type = models.CharField(max_length=255)
    tradingExchange = models.CharField(max_length=255)
    country = models.CharField(max_length=255, null=True, blank=True)
    logoUrl = models.CharField(max_length=255, null=True, blank=True)
    localizedName = models.CharField(max_length=255)
    routes = models.TextField()
    barSource = models.CharField(max_length=255)
    hasIntraday = models.BooleanField()
    hasDaily = models.BooleanField()
