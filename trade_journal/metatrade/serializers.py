from rest_framework import serializers
from .models import MetaTraderAccount


class MetaTraderAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetaTraderAccount
        fields = ['id', 'is_active']
