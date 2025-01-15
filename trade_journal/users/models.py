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
    credentials  = models.CharField(max_length=256, null=True)
    currency = models.CharField(max_length=10, null=True, default='USD')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user.id,
            'account_name': self.account_name,
            'balance': self.balance,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'cached_until': self.cached_until,
            'status': self.status,
            'platform': self.platform,
            'currency': self.currency,
        }

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
            'price': self.open_price,
            'gain': self.gain,
            'profit': self.profit,
            'total_amount': self.quantity,
            'trade_date': self.open_time,
            'close_date': self.close_time,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'duration_in_minutes': self.duration_in_minutes,
            'currency': self.account.currency,
        }

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

        return f'uploaded_files/{name}/{filename}'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_files')
    file = models.ImageField(upload_to=upload_location, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Uploaded file for {self.user}"
