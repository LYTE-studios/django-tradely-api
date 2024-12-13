from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class MetaTraderAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account_name = models.CharField(max_length=255)
    account_id = models.CharField(max_length=255, null=True)
    api_token = models.CharField(max_length=255)
    email = models.EmailField(unique=False, null=True)
    password = models.TextField(null=True)
    key_code = models.BinaryField(null=True)
    server = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s MetaTrader Account"


class Trade(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    account_id = models.CharField(max_length=255)
    volume = models.FloatField(default=0, null=True, blank=True)
    duration_in_minutes = models.FloatField(default=0, null=True, blank=True)
    profit = models.FloatField(default=0, null=True, blank=True)
    gain = models.FloatField(default=0, null=True, blank=True)
    success = models.CharField(max_length=255, null=True, blank=True)
    open_time = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f'Trade {self.trade_id} for user {self.user_id}'
