from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class CTraderAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account = models.CharField(max_length=255)
    password = models.TextField(null=True)
    key_code = models.BinaryField(null=True)
    server = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    demo_status = models.BooleanField(default=True)  # demo mode status
    balance = models.FloatField(default=0)
    account_name = models.CharField(null=True)

    def to_dict(self):
        return {
            'id': self.id,
            'account': self.account,
            'server': self.server,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'balance': self.balance,
            'account_name': self.account_name,
        }

    def __str__(self):
        return f"{self.user.username}'s MetaTrader Account"


class CTrade(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    order_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    side = models.CharField(max_length=255)
    amount = models.FloatField(null=True, blank=True)
    price = models.FloatField(null=True, blank=True)
    actual_price = models.FloatField(null=True, blank=True)
    pos_id = models.CharField(max_length=255, null=True, blank=True)
    clid = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f'Trade {self.id} for user {self.user_id}'
