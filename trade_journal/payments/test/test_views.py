from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from ..models import Payment
from ..views import PaymentViewSet

User = get_user_model()


class PaymentViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        self.payment = Payment.objects.create(
            user=self.user,
            stripe_payment_intent_id='pi_test123',
            amount=100.00,
            currency='USD',
            status='pending'
        )

    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent(self, mock_create):
        mock_create.return_value = MagicMock(id='pi_test456', client_secret='secret_test')
        url = reverse('payment-create-payment-intent')
        data = {'amount': 100.00, 'currency': 'USD'}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('clientSecret', response.data)
        self.assertIn('payment_id', response.data)

    @patch('stripe.PaymentIntent.retrieve')
    def test_check_status(self, mock_retrieve):
        mock_retrieve.return_value = MagicMock(status='succeeded')
        url = reverse('payment-check-status', kwargs={'pk': self.payment.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'succeeded')

    @patch('stripe.Webhook.construct_event')
    def test_stripe_webhook_payment_succeeded(self, mock_construct_event):
        event_data = {
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': self.payment.stripe_payment_intent_id,
                }
            }
        }
        mock_construct_event.return_value = event_data
        url = reverse('payment-stripe-webhook')
        response = self.client.post(url, data={}, HTTP_STRIPE_SIGNATURE='test_signature')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'succeeded')

    @patch('stripe.Webhook.construct_event')
    def test_stripe_webhook_payment_failed(self, mock_construct_event):
        event_data = {
            'type': 'payment_intent.payment_failed',
            'data': {
                'object': {
                    'id': self.payment.stripe_payment_intent_id,
                }
            }
        }
        mock_construct_event.return_value = event_data
        url = reverse('payment-stripe-webhook')
        response = self.client.post(url, data={}, HTTP_STRIPE_SIGNATURE='test_signature')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'failed')

    @patch('payments.views.send_email_provider')
    def test_send_payment_confirmation_email(self, mock_send_email):
        mock_send_email.return_value = True
        viewset = PaymentViewSet()
        viewset.send_payment_confirmation_email(self.payment, 'TestService', 'test_api_key', 'test_api_secret')

        mock_send_email.assert_called_once()
        args = mock_send_email.call_args[0]
        self.assertEqual(args[0], 'TestService')
        self.assertEqual(args[1], 'test_api_key')
        self.assertEqual(args[2], 'test_api_secret')
        self.assertEqual(args[3], 'Payment Confirmation')
        self.assertIn(str(self.payment.amount), args[4])
        self.assertEqual(args[5], [self.user.email])

    @patch('payments.views.send_email_provider')
    def test_send_payment_failure_email(self, mock_send_email):
        mock_send_email.return_value = True
        viewset = PaymentViewSet()
        viewset.send_payment_failure_email(self.payment, 'TestService', 'test_api_key', 'test_api_secret')

        mock_send_email.assert_called_once()
        args = mock_send_email.call_args[0]
        self.assertEqual(args[0], 'TestService')
        self.assertEqual(args[1], 'test_api_key')
        self.assertEqual(args[2], 'test_api_secret')
        self.assertEqual(args[3], 'Payment Failed')
        self.assertIn(str(self.payment.amount), args[4])
        self.assertEqual(args[5], [self.user.email])