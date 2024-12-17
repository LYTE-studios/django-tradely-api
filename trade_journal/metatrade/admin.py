from django.contrib import admin

from .models import MetaTraderAccount, Trade

# Register your models here.

admin.site.register(MetaTraderAccount)
admin.site.register(Trade)
