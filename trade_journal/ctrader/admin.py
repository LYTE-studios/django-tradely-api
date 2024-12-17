from django.contrib import admin

from .models import CTraderAccount, CTrade

# Register your models here.

admin.site.register(CTraderAccount)
admin.site.register(CTrade)
