from rest_framework import serializers
from .models import Payment

from django.contrib.auth import get_user_model


User = get_user_model()


class PaymentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=False)

    class Meta:
        model = Payment
        fields = ['id', 'stripe_payment_intent_id', 'amount', 'currency', 'status', 'created_at', 'user']
        read_only_fields = ['id', 'stripe_payment_intent_id', 'status', 'created_at']


class PaymentIntentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3, default='EUR')


class SendEmailSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255, required=True)
    message = serializers.CharField(required=True)
    recipient_list = serializers.ListField(
        child=serializers.EmailField(),  # Ensure each recipient is a valid email address
        required=True
    )
    deliver_time = serializers.DateTimeField(default=False)
    email_service_name = serializers.CharField(max_length=255)
    email_service_api_key = serializers.CharField(max_length=255)
    email_service_api_secret = serializers.CharField(max_length=255, required=False)
