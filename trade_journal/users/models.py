from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.conf import settings


class CustomUser(AbstractUser):
    # Any additional fields can go here
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(null=True, blank=True)


class TradeAccount(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trade_accounts')
    name = models.CharField(max_length=100)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - ${self.balance}"


class ManualTrade(models.Model):
    TRADE_TYPES = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell')
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='manual_trades')
    trade_type = models.CharField(max_length=4, choices=TRADE_TYPES)
    symbol = models.CharField(max_length=10)  # e.g., AAPL, GOOGL
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=15, decimal_places=2)
    profit = models.FloatField(default=0.0, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    trade_date = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Calculate total amount if not provided
        if not self.total_amount:
            self.total_amount = self.quantity * self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.trade_type} {self.quantity} {self.symbol} at ${self.price}"


class TradeNote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trade_notes')
    trade = models.ForeignKey(ManualTrade, on_delete=models.CASCADE, related_name='trade_notes', null=True, blank=True)
    note_date = models.DateField(null=True, blank=True)
    trade_note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Note for {self.trade.symbol} trade" if self.trade else f"Note for {self.note_date}"
