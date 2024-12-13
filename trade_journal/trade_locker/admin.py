from django.contrib import admin

# Register your models here.

from .models import TraderLockerAccount, OrderHistory

admin.site.register(TraderLockerAccount)    
admin.site.register(OrderHistory)   