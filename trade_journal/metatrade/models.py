from django.db import models
from django.contrib.auth import get_user_model

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
    user_id = models.CharField(max_length=255)
    account_id = models.CharField(max_length=255, null=True)
    trade_id = models.CharField(max_length=255)
    symbol = models.CharField(max_length=10)
    volume = models.FloatField()
    price_open = models.FloatField()
    price_close = models.FloatField()
    profit = models.FloatField()
    create_time = models.DateTimeField()
    close_time = models.DateTimeField()

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'account_id': self.account_id,
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'volume': self.volume,
            'price_open': self.price_open,
            'price_close': self.price_close,
            'profit': self.profit,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'close_time': self.close_time.isoformat() if self.close_time else None,
        }

    def __str__(self):
        return f'Trade {self.trade_id} for user {self.account_id}'
