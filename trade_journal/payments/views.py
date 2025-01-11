import stripe
from anymail.message import AnymailMessage
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .email_service import get_dynamic_email_backend
from .models import Email
from .models import Payment
from .serializers import PaymentSerializer, PaymentIntentSerializer

stripe.api_key = settings.STRIPE_SECRET_KEY


def send_email_message(subject, message, recipient_list, email_backend):
    # Create the email message
    email = AnymailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipient_list,
        connection=email_backend
    )
    # Send the email
    email.send()


def send_email_provider(service_name, api_key, api_secret, subject, message, recipient_list):
    # get service name and api key and api secret

    mail_credentials = {'api_key': api_key}
    if api_secret:
        mail_credentials['api_secret'] = api_secret

    if not service_name or not api_key or (service_name == 'Mailjet' and not api_secret):
        return False

    email_backend = get_dynamic_email_backend(service_name, mail_credentials)

    email_record = Email.objects.create(
        subject=subject,
        message=message,
        recipient_list=','.join(recipient_list),
        sent_mail_status='pending',  # Initial status,
    )
    try:
        # Send the email
        send_email_message(subject, message, recipient_list, email_backend)

        # Update status to 'sent'
        email_record.sent_mail_status = 'sent'
        email_record.save()
        return True

    except Exception as e:
        # Update status to 'failed'
        email_record.sent_mail_status = 'failed'
        email_record.save()

        return False


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def create_payment_intent(self, request):
        service_name = request.email_service_name
        api_key = request.email_service_api_key
        api_secret = request.email_service_api_secret if service_name == 'Mailjet' else None
        serializer = PaymentIntentSerializer(data=request.data)
        if serializer.is_valid():
            amount = int(serializer.validated_data['amount'] * 100)  # Convert to cents
            currency = serializer.validated_data['currency']

            try:
                intent = stripe.PaymentIntent.create(
                    amount=amount,
                    currency=currency,
                    metadata={'user_id': request.user.id}
                )
                payment = Payment.objects.create(
                    user=request.user,
                    stripe_payment_intent_id=intent.id,
                    amount=serializer.validated_data['amount'],
                    currency=currency
                )
                self.send_payment_confirmation_email(payment, service_name, api_key, api_secret)
                
                return Response({
                    'clientSecret': intent.client_secret,
                    'payment_id': payment.id
                })
            except stripe.error.StripeError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def check_status(self, request, pk=None):
        payment = self.get_object()
        intent = stripe.PaymentIntent.retrieve(payment.stripe_payment_intent_id)
        return Response({'status': intent.status})

    @action(detail=False, methods=['post'])
    def stripe_webhook(self, request):
        payload = request.body
        sig_header = request.META['HTTP_STRIPE_SIGNATURE']
        service_name = request.email_service_name
        api_key = request.email_service_api_key
        api_secret = request.email_service_api_secret if service_name == 'Mailjet' else None
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            payment = Payment.objects.get(stripe_payment_intent_id=payment_intent['id'])
            payment.status = 'succeeded'
            payment.save()
            self.send_payment_confirmation_email(payment, service_name, api_key, api_secret)
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            payment = Payment.objects.get(stripe_payment_intent_id=payment_intent['id'])
            payment.status = 'failed'
            payment.save()
            self.send_payment_failure_email(payment, service_name, api_key, api_secret)

        return Response(status=status.HTTP_200_OK)

    def send_payment_confirmation_email(self, payment, service_name, api_key, api_secret):
        subject = 'Payment Confirmation'
        message = f'Your payment of {payment.amount} {payment.currency} has been successfully processed.'
        send_email_provider(service_name, api_key, api_secret, subject, message, [payment.user.email])

    def send_payment_failure_email(self, payment, service_name, api_key, api_secret):
        subject = 'Payment Failed'
        message = f'Your payment of {payment.amount} {payment.currency} has failed. Please try again or contact support.'
        send_email_provider(service_name, api_key, api_secret, subject, message, [payment.user.email])
