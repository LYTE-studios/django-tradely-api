from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

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

    account = models.ForeignKey(TradeAccount, on_delete=models.CASCADE, related_name='manual_trades', null=True,
                                blank=True)
    trade_type = models.CharField(max_length=4, choices=TRADE_TYPES)
    symbol = models.CharField(max_length=10, null=True, default='')  # e.g., AAPL, GOOGL
    quantity = models.IntegerField(null=True, blank=True, default=1)
    price = models.DecimalField(max_digits=15, decimal_places=2, null=True, default=0)
    profit = models.FloatField(default=0.0, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, default=0)
    trade_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_dict(self):
        return {
            'id': self.id,
            'trade_type': self.trade_type,
            'symbol': self.symbol,
            'quantity': self.quantity,
            'price': self.price,
            'profit': self.profit,
            'total_amount': self.total_amount,
            'trade_date': self.trade_date,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    @staticmethod
    def from_c_trade(c_trade):
        return ManualTrade(
            trade_type=c_trade.side,
            symbol=c_trade.name,
            quantity=c_trade.amount,
            price=c_trade.price,
            profit=c_trade.actual_price - c_trade.price,
            total_amount=c_trade.amount * c_trade.price,
            trade_date=c_trade.open_time
        )
    
    @staticmethod
    def from_metatrade(metatrade_trade):

        # Set the trade type
        trade_type = 'SELL'
        if metatrade_trade.type == 'DEAL_TYPE_BUY':
            trade_type = 'BUY'

        # Set the symbol
        symbol = metatrade_trade.symbol

        # Set the quantity
        quantity = metatrade_trade.volume

        # Set the profit
        profit = metatrade_trade.profit

        # Set the trade date
        trade_date = metatrade_trade.open_time

        return ManualTrade(
            trade_type=trade_type,
            symbol=symbol,
            quantity=quantity,
            price=metatrade_trade.profit,
            profit=profit,
            total_amount=metatrade_trade.profit * quantity,
            trade_date=trade_date
        )

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
