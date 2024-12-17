# trade_journal/metatrade/tests.py
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import asyncio

from django.contrib.auth import get_user_model
from django.test import AsyncClient, TestCase
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase
from django.urls import reverse
from rest_framework import status

from users.models import CustomUser
from .models import MetaTraderAccount, Trade
from .services import MetaApiService

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
            password=b'encrypted_password',
            key_code=b'key_code',
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
    @patch('metatrade.services.MetaApiService.refresh_caches')
    def test_login_account(self, mock_refresh_caches, mock_encrypt_password, MockMetaApi):
        mock_encrypt_password.return_value = b'encrypted_password'
        mock_refresh_caches.return_value = None
        
        mock_meta_api = MockMetaApi.return_value
        mock_meta_account = MagicMock()
        mock_meta_account.id = '12345'
        mock_meta_account.name = 'test_account'

        async def async_create_account(*args, **kwargs):
            return mock_meta_account
        
        mock_meta_api.metatrader_account_api.create_account = async_create_account

        url = reverse('metatrade_login')
        data = {
            'server_name': 'server_name',
            'username': 'user1@example.com',
            'password': 'password',
            'platform': 'mt4',
            'account_name': 'test_account'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Login successful.')

    @patch('metatrade.views.MetaApi')
    def test_login_account_api_error(self, MockMetaApi):
        mock_meta_api = MockMetaApi.return_value
        
        class MetaApiError(Exception):
            def __str__(self):
                return "API error"
        
        async def async_error(*args, **kwargs):
            raise MetaApiError()
        
        mock_meta_api.metatrader_account_api.create_account = async_error

        url = reverse('metatrade_login')
        data = {
            'server_name': 'server_name',
            'username': 'user1@example.com',
            'password': 'password',
            'platform': 'platform'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], "API error")

class MetaApiServiceTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.meta_account = MetaTraderAccount.objects.create(
            user=self.user,
            account_id='test123',
            balance=1000
        )

    @patch('metatrade.services.MetaApi')
    def test_refresh_account(self, mock_meta_api):
        service = MetaApiService()
        
        mock_meta_api_instance = MagicMock()
        mock_meta_api.return_value = mock_meta_api_instance
        
        mock_account = MagicMock()
        mock_meta_api_instance.metatrader_account_api.get_account.return_value = mock_account
        
        mock_connection = MagicMock()
        mock_account.get_rpc_connection.return_value = mock_connection
        mock_connection.get_account_information.return_value = {'balance': 2000}

        with patch.object(service, 'get_meta_trades', return_value=[]):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(service.refresh_account(self.meta_account, self.user))
            loop.close()

        self.meta_account.refresh_from_db()
        self.assertEqual(self.meta_account.balance, 2000)

    def test_cache_manager(self):
        account = self.meta_account
        account.cached_at = timezone.now() - timedelta(minutes=40)
        account.cached_until = timezone.now() - timedelta(minutes=10)
        account.save()

        service = MetaApiService()
        self.assertTrue(service.cache_manager.needs_refresh(
            account.cached_at,
            account.cached_until
        ))

    @patch('metatrade.services.MetaApiService.refresh_caches_sync')
    def test_fetch_trades(self, mock_refresh):
        Trade.objects.create(
            user=self.user,
            account_id=self.meta_account.account_id,
            trade_id='trade1',
            profit=100
        )

        trades = MetaApiService.fetch_trades(self.user)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]['profit'], 100)