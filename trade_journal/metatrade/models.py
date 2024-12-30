from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class MetaTraderAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account_id = models.CharField(max_length=255, null=True)
    account_name = models.CharField(max_length=255)
    email = models.EmailField(unique=False, null=True)
    password = models.TextField(null=True)
    key_code = models.BinaryField(null=True)
    server = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cached_at = models.DateTimeField(null=True)
    cached_until = models.DateTimeField(null=True)
    balance = models.FloatField(default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user.id,
            'account_id': self.account_id,
            'account_name': self.account_name,
            'email': self.email,
            'server': self.server,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'cached_at': self.cached_at.isoformat() if self.cached_at else None,
            'cached_until': self.cached_until.isoformat() if self.cached_until else None,
            'balance': self.balance
        }

    def __str__(self):
        return f"{self.user.username}'s MetaTrader Account"


class Trade(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    account_id = models.CharField(max_length=255, null=True)
    trade_id = models.CharField(max_length=255, null=True)
    symbol = models.CharField(max_length=255, null=True)
    volume = models.FloatField(default=0, null=True, blank=True)
    duration_in_minutes = models.FloatField(default=0, null=True, blank=True)
    profit = models.FloatField(default=0, null=True, blank=True)
    gain = models.FloatField(default=0, null=True, blank=True)
    success = models.CharField(max_length=255, null=True, blank=True)
    open_time = models.DateTimeField(blank=True)
    close_time = models.DateTimeField(blank=True, null=True)
    type = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f'Trade {self.id} for user {self.account_id}'
