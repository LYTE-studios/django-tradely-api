# trade_journal/metatrade/tests.py
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import MetaTraderAccount

User = get_user_model()


class MetaTraderAccountViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='user1', email='user1@example.com', password='password')
        self.client.force_authenticate(user=self.user)
        self.account = MetaTraderAccount.objects.create(
            user=self.user,
            account_id='12345',
            email='user1@example.com',
            password=b'encrypted_password',  # Encode the password as bytes
            key_code=b'key_code',  # Encode the key_code as bytes
            server='server_name',
            account_name='account_name'
        )

    def test_delete_account(self):
        url = reverse('delete_account', kwargs={'account_id': self.account.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Account deleted.')
        self.assertFalse(MetaTraderAccount.objects.filter(id=self.account.id).exists())

    @patch('metatrade.views.MetaApi')
    @patch('metatrade.views.encrypt_password')
    def test_login_account(self, mock_encrypt_password, MockMetaApi):
        mock_encrypt_password.return_value = b'encrypted_password'  # Encode the password as bytes
        mock_meta_api = MockMetaApi.return_value
        mock_meta_account = MagicMock()
        mock_meta_api.metatrader_account_api.create_account.return_value = mock_meta_account
        mock_meta_account.id = '12345'
        mock_meta_account.name = 'account_name'

        url = reverse('metatrade_login')
        data = {
            'server_name': 'server_name',
            'username': 'user1@example.com',
            'password': 'password',
            'platform': 'platform'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Login successful.')
        self.assertEqual(response.data['email'], 'user1@example.com')
        self.assertEqual(response.data['user_id'], self.user.id)
        self.assertTrue(MetaTraderAccount.objects.filter(account_id='12345').exists())

    def test_login_account_missing_fields(self):
        url = reverse('metatrade_login')
        data = {
            'server_name': 'server_name',
            'username': '',
            'password': 'password',
            'platform': 'platform'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'All fields are required: server_name, username, and password.')

    @patch('metatrade.views.MetaApi')
    def test_login_account_api_error(self, MockMetaApi):
        mock_meta_api = MockMetaApi.return_value
        mock_meta_api.metatrader_account_api.create_account.side_effect = Exception('API error')

        url = reverse('metatrade_login')
        data = {
            'server_name': 'server_name',
            'username': 'user1@example.com',
            'password': 'password',
            'platform': 'platform'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'API error')
