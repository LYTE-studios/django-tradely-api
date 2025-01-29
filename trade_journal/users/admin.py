from django.contrib import admin

# Register your models here.

from .models import CustomUser, TradeAccount, ManualTrade, TradeNote

admin.site.register(CustomUser)
admin.site.register(TradeAccount)
admin.site.register(ManualTrade)
admin.site.register(TradeNote)  