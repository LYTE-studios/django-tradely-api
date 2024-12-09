from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class MetaTraderAccount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    api_token = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s MetaTrader Account"


class Trade(models.Model):
    user_id = models.CharField(max_length=255)
    trade_id = models.CharField(max_length=255)
    symbol = models.CharField(max_length=10)
    volume = models.FloatField()
    price_open = models.FloatField()
    price_close = models.FloatField()
    profit = models.FloatField()
    create_time = models.DateTimeField()
    close_time = models.DateTimeField()

    def __str__(self):
        return f'Trade {self.trade_id} for user {self.user_id}'
