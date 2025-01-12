from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class CustomUser(AbstractUser):
    # Any additional fields can go here
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(null=True, blank=True)

# -- Trade specific --

class AccountStatus(models.TextChoices):
    active = 'Active'
    inactive = 'Inactive'

class Platform(models.TextChoices):
    meta_trader_4 = 'MetaTrader4'
    meta_trader_5 = 'MetaTrader5'
    trade_locker = 'TradeLocker'
    c_trader =  'CTrader'
    manual =  'Manual'

class TradeType(models.TextChoices):
    buy = 'Buy'
    sell = 'Sell'

class TradeAccount(models.Model):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trade_accounts')

    account_id = models.CharField(max_length=255, null=True)
    account_name = models.CharField(max_length=255, null=True)

    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    cached_at = models.DateTimeField(null=True)
    cached_until = models.DateTimeField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    platform = models.CharField(max_length=64, choices=Platform.choices, default=Platform.manual)
    status = models.CharField(max_length=64, choices=AccountStatus.choices, default=AccountStatus.active)

    currency = models.CharField(max_length=10, null=True, default='USD')

    def __str__(self):
        return f"{self.name} - ${self.balance}"


class ManualTrade(models.Model):
    
    account = models.ForeignKey(TradeAccount, on_delete=models.CASCADE, related_name='manual_trades', null=True,
                                blank=True)
    
    # Foreign Reference
    exchange_id = models.CharField(max_length=64, null=True)

    # BUY or SELL
    trade_type = models.CharField(max_length=4, choices=TradeType, null=True, blank=True)

    # Trade Symbol
    symbol = models.CharField(max_length=10, null=True, default='')

    # Lot size
    quantity = models.IntegerField(null=True, blank=True, default=1)

    # Price at open time
    open_price = models.DecimalField(max_digits=25, decimal_places=5, null=True)
    close_price = models.DecimalField(max_digits=25, decimal_places=5, null=True)

    # NET ROI Gain
    gain = models.FloatField(default=0.0, null=True, blank=True)

    # Profit in symbol currency
    profit = models.FloatField(default=0.0, null=True, blank=True)
    
    # Open - Close time
    open_time = models.DateTimeField(null=True, blank=True)
    close_time = models.DateTimeField(null=True, blank=True)

    # Duration of the trade
    duration_in_minutes = models.FloatField(default=0, null=True, blank=True)

    # Checks if the trade is an account balance modifier
    is_top_up = models.BooleanField(default=False, blank=True)

    # System
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_dict(self):
        return {
            'id': self.id,
            'trade_type': self.trade_type,
            'symbol': self.symbol,
            'quantity': self.quantity,
            'price': self.price,
            'gain': self.gain,
            'profit': self.profit,
            'total_amount': self.total_amount,
            'trade_date': self.trade_date,
            'close_date': self.close_date,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'duration_in_minutes': self.duration_in_minutes,
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

        close_date = metatrade_trade.close_time

        gain = metatrade_trade.gain

        return ManualTrade(
            trade_type=trade_type,
            symbol=symbol,
            quantity=quantity,
            price=metatrade_trade.profit,
            gain=gain,
            profit=profit,
            total_amount=metatrade_trade.profit * quantity,
            trade_date=trade_date,
            close_date=close_date,
            duration_in_minutes=metatrade_trade.duration_in_minutes
        )

    def save(self, *args, **kwargs):
        # Calculate total amount if not provided
        if not self.total_amount:
            self.total_amount = self.quantity * self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.trade_type} {self.quantity} {self.symbol} at ${self.price}"


# -- Note specific --

class TradeNote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trade_notes')
    trade = models.ForeignKey(ManualTrade, on_delete=models.CASCADE, related_name='trade_notes', null=True, blank=True)
    note_date = models.DateField(null=True, blank=True)
    trade_note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Note for {self.trade.symbol} trade" if self.trade else f"Note for {self.note_date}"
    

class UploadedFile(models.Model):
        
    def upload_location(instance, filename):
        extension = filename.split('.')[-1]

        from django.utils import timezone

        now = timezone.now()

        name = int(now.timestamp())

        return f'uploaded_files/{now.year}/{now.month}/{name}.{extension}'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_files')
    file = models.FileField(upload_to=upload_location)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Uploaded file for {self.user}"
