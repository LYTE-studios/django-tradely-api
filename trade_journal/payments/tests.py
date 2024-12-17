# tests.py
import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .email_service import get_dynamic_email_backend
from .models import Payment
from .serializers import PaymentSerializer, PaymentIntentSerializer, SendEmailSerializer

User = get_user_model()


class TestGetDynamicEmailBackend(unittest.TestCase):

    @patch('payments.email_service.import_module')
    def test_mailjet_backend(self, mock_import_module):
        mock_backend_class = MagicMock()
        mock_import_module.return_value = mock_backend_class
        credentials = {'api_key': 'test_key', 'api_secret': 'test_secret'}

        backend = get_dynamic_email_backend('Mailjet', credentials)

        mock_import_module.assert_called_once_with('anymail.backends.mailjet')
        mock_backend_class.EmailBackend.assert_called_once_with(api_key='test_key', secret_key='test_secret')
        self.assertEqual(backend, mock_backend_class.EmailBackend())

    @patch('payments.email_service.import_module')
    def test_mailersend_backend(self, mock_import_module):
        mock_backend_class = MagicMock()
        mock_import_module.return_value = mock_backend_class
        credentials = {'api_key': 'test_key'}

        backend = get_dynamic_email_backend('MailerSend', credentials)

        mock_import_module.assert_called_once_with('anymail.backends.mailersend')
        mock_backend_class.EmailBackend.assert_called_once_with(api_token='test_key')
        self.assertEqual(backend, mock_backend_class.EmailBackend())


    @patch('payments.email_service.import_module')
    def test_postmark_backend(self, mock_import_module):
        mock_backend_class = MagicMock()
        mock_import_module.return_value = mock_backend_class
        credentials = {'api_key': 'test_key'}

        backend = get_dynamic_email_backend('Postmark', credentials)

        mock_import_module.assert_called_once_with('anymail.backends.postmark')
        mock_backend_class.EmailBackend.assert_called_once_with(server_token='test_key')
        self.assertEqual(backend, mock_backend_class.EmailBackend())

    def test_unsupported_service(self):
        with self.assertRaises(ValueError) as context:
            get_dynamic_email_backend('UnsupportedService', {})

        self.assertEqual(str(context.exception), 'Unsupported email service: UnsupportedService')


class PaymentSerializerTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', email='user1@example.com', password='password')
        self.payment_data = {
            'stripe_payment_intent_id': 'pi_12345',
            'amount': Decimal('100.00'),
            'currency': 'USD',
            'status': 'succeeded',
            'created_at': datetime.now(),
            'user': self.user
        }
        self.payment = Payment.objects.create(**self.payment_data)

    def test_payment_serializer(self):
        serializer = PaymentSerializer(instance=self.payment)
        data = serializer.data
        self.assertEqual(set(data.keys()),
                         set(['id', 'stripe_payment_intent_id', 'amount', 'currency', 'status', 'created_at', 'user']))
        self.assertEqual(data['stripe_payment_intent_id'], self.payment_data['stripe_payment_intent_id'])
        self.assertEqual(data['amount'], str(self.payment_data['amount']))
        self.assertEqual(data['currency'], self.payment_data['currency'])
        self.assertEqual(data['status'], self.payment_data['status'])
        self.assertEqual(data['user'], self.user.id)  # Compare with user.id instead of user object


class PaymentIntentSerializerTest(APITestCase):
    def test_payment_intent_serializer(self):
        data = {
            'amount': Decimal('100.00'),
            'currency': 'USD'
        }
        serializer = PaymentIntentSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['amount'], data['amount'])
        self.assertEqual(serializer.validated_data['currency'], data['currency'])


class SendEmailSerializerTest(APITestCase):
    def test_send_email_serializer(self):
        from django.utils import timezone
        data = {
            'subject': 'Test Subject',
            'message': 'Test Message',
            'recipient_list': ['test@example.com'],
            'deliver_time': timezone.now(),  # Use timezone-aware datetime
            'email_service_name': 'Mailjet',
            'email_service_api_key': 'test_api_key',
            'email_service_api_secret': 'test_api_secret'
        }
        serializer = SendEmailSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['subject'], data['subject'])
        self.assertEqual(serializer.validated_data['message'], data['message'])
        self.assertEqual(serializer.validated_data['recipient_list'], data['recipient_list'])
        # Compare timestamps instead of full datetime objects
        self.assertEqual(
            serializer.validated_data['deliver_time'].timestamp(),
            data['deliver_time'].timestamp()
        )
        self.assertEqual(serializer.validated_data['email_service_name'], data['email_service_name'])
        self.assertEqual(serializer.validated_data['email_service_api_key'], data['email_service_api_key'])
        self.assertEqual(serializer.validated_data['email_service_api_secret'], data['email_service_api_secret'])

    def test_send_email_serializer_missing_fields(self):
        data = {
            'subject': 'Test Subject',
            'message': 'Test Message',
            'recipient_list': ['test@example.com'],
            'email_service_name': 'Mailjet',
            'email_service_api_key': 'test_api_key'
        }
        serializer = SendEmailSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['subject'], data['subject'])
        self.assertEqual(serializer.validated_data['message'], data['message'])
        self.assertEqual(serializer.validated_data['recipient_list'], data['recipient_list'])
        self.assertEqual(serializer.validated_data['email_service_name'], data['email_service_name'])
        self.assertEqual(serializer.validated_data['email_service_api_key'], data['email_service_api_key'])
        self.assertNotIn('email_service_api_secret', serializer.validated_data)
