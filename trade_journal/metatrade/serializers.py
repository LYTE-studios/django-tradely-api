from rest_framework import serializers
from .models import MetaTraderAccount


class MetaTraderAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetaTraderAccount
        fields = ['id', 'api_token', 'is_active']
        extra_kwargs = {'api_token': {'write_only': True}}
