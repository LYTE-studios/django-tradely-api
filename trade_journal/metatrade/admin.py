from django.contrib import admin

# Register your models here.

from .models import MetaTraderAccount, Trade

admin.site.register(MetaTraderAccount)
admin.site.register(Trade)  