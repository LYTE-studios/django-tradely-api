from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import TradeAccount, ManualTrade, TradeNote
from .models import CustomUser
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("username", "email", "password")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):

        email = validated_data.get("email")

        whitelist = "tradely.io"

        if whitelist in email:
            user = User(**validated_data)
            user.set_password(validated_data["password"])
            user.save()
            return user
        else:
            raise serializers.ValidationError("Email not allowed")


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "username", "email", "first_name", "last_name", "date_of_birth"]


class TradeAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradeAccount
        fields = [
            "id",
            "account_name",
            "balance",
            "created_at",
            "updated_at",
            "platform",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "platform",
            "disabled",
        ]

    def validate_balance(self, value):
        if value < 0:
            raise serializers.ValidationError("Balance cannot be negative.")
        return value


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordChangeSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            uid = urlsafe_base64_decode(data["uid"]).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid UID")

        if not default_token_generator.check_token(user, data["token"]):
            raise serializers.ValidationError("Invalid token")

        return data

    def save(self):
        uid = urlsafe_base64_decode(self.validated_data["uid"]).decode()
        user = User.objects.get(pk=uid)
        user.set_password(self.validated_data["new_password"])
        user.save()


# class ManualTradeSerializer(serializers.ModelSerializer):
#     total_amount = serializers.DecimalField(
#         max_digits=15,
#         decimal_places=2,
#         read_only=True
#     )

#     class Meta:
#         model = ManualTrade
#         fields = [
#             'id', 'account', 'trade_type', 'symbol',
#             'quantity', 'price', 'profit', 'total_amount',
#             'trade_date', 'created_at', 'updated_at'
#         ]
#         read_only_fields = ['id', 'created_at', 'updated_at', 'total_amount']

#     def validate(self, data):
#         # Validate trade data
#         if data.get('quantity', 0) <= 0:
#             raise serializers.ValidationError("Quantity must be greater than 0.")

#         if data.get('price', 0) <= 0:
#             raise serializers.ValidationError("Price must be greater than 0.")

#         # Validate that the account belongs to the user making the request
#         request = self.context.get('request')
#         if request and request.user:
#             account = data.get('account')
#             if account and account.user != request.user:
#                 raise serializers.ValidationError("You can only create trades for your own accounts.")

#         return data

#     def create(self, validated_data):
#         # Calculate total amount during creation
#         validated_data['total_amount'] = (
#                 Decimal(str(validated_data['quantity'])) *
#                 Decimal(str(validated_data['price']))
#         )
#         return super().create(validated_data)


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
    trade_distribution = serializers.DictField(child=serializers.IntegerField())


class TradeNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradeNote
        fields = [
            "id",
            "user",
            "trade",
            "trade_note",
            "note_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user"]

    def validate(self, data):
        # If no trade is provided during update, keep the existing trade
        if not data.get("trade") and not data.get("note_date"):
            raise serializers.ValidationError(
                "Either trade or note_date must be provided"
            )

        # Validate that the trade belongs to the user's account
        request = self.context.get("request")
        if request and request.user:
            trade = data.get("trade")
            if trade and trade.account.user != request.user:
                raise serializers.ValidationError(
                    "You can only create notes for trades in your accounts."
                )

        return data

    def create(self, validated_data):
        # Ensure the user is set from the request
        request = self.context.get("request")
        if request and request.user:
            validated_data["user"] = request.user

        note, created = TradeNote.objects.update_or_create(
            note_date=validated_data["note_date"],
            user=validated_data["user"],
            defaults=validated_data,
        )

        return note
