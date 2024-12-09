from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import TradeAccount, ManualTrade, TradeNote
from decimal import Decimal

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

class TradeAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradeAccount
        fields = ['id', 'name', 'balance', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_balance(self, value):
        # Ensure balance is not negative
        if value < 0:
            raise serializers.ValidationError("Balance cannot be negative.")
        return value

class ManualTradeSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )

    class Meta:
        model = ManualTrade
        fields = [
            'id', 'account', 'trade_type', 'symbol', 
            'quantity', 'price', 'total_amount', 
            'trade_date', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_amount']

    def validate(self, data):
        # Validate trade data
        if data.get('quantity', 0) <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        
        if data.get('price', 0) <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        
        # Ensure the trade account belongs to the current user
        account = data.get('account')
        if not account or account.user != self.context['request'].user:
            raise serializers.ValidationError("You can only create trades for your own accounts.")
        
        return data

    def create(self, validated_data):
        # Calculate total amount during creation
        validated_data['total_amount'] = (
            Decimal(str(validated_data['quantity'])) * 
            Decimal(str(validated_data['price']))
        )
        return super().create(validated_data)

class TradeStatisticsSerializer(serializers.Serializer):
    """
    Serializer for presenting structured trade statistics
    """
    total_trades = serializers.IntegerField()
    total_invested = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_trade_size = serializers.DecimalField(max_digits=15, decimal_places=2)
    unique_symbols = serializers.ListField(child=serializers.CharField())

class SymbolPerformanceSerializer(serializers.Serializer):
    """
    Serializer for symbol-level trade performance
    """
    symbol = serializers.CharField()
    total_trades = serializers.IntegerField()
    total_quantity = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    avg_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    trade_distribution = serializers.DictField(
        child=serializers.IntegerField()
    )

class TradeNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradeNote
        fields = ['id', 'trade', 'trade_note', 'note_date', 'created_at', 'updated_at']
        extra_kwargs = {
            'user': {'read_only': True},
            'trade': {'required': False}
        }
    
    def validate(self, data):
        # If no trade is provided during update, keep the existing trade
        if not data.get('trade') and not data.get('note_date'):
            raise serializers.ValidationError("Either trade or note_date must be provided")
        return data

    def update(self, instance, validated_data):
        # Ensure user is not changed during update
        validated_data.pop('user', None)
        return super().update(instance, validated_data)
    