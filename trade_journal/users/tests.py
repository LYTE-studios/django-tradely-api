from rest_framework import status
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.test import APITestCase

from .models import TradeAccount, ManualTrade, TradeNote

User = get_user_model()


class HelloThereViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='user1', email='user1@example.com', password='password')
        self.client.force_authenticate(user=self.user)

    def test_hello_there_view(self):
        response = self.client.post('/api/users//hello-there/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class UserLoginViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', email='user1@example.com', password='password')

    def test_user_login_view(self):
        data = {
            'username': 'user1',
            'password': 'password'
        }
        response = self.client.post('/api/users/login/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_user_login_view_invalid_credentials(self):
        data = {
            'username': 'user1',
            'password': 'wrongpassword'
        }
        response = self.client.post('/api/users/login/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], 'Invalid credentials')


class TradeAccountViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='user1', email='user1@example.com', password='password')
        self.client.force_authenticate(user=self.user)
        self.trade_account = TradeAccount.objects.create(user=self.user, name='Test Account')

    def test_trade_account_view_set(self):
        response = self.client.get('/api/users/trade-accounts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Test Account')


class ManualTradeViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='user1', email='user1@example.com', password='password')
        self.client.force_authenticate(user=self.user)
        self.trade_account = TradeAccount.objects.create(user=self.user, name='Test Account')
        self.manual_trade = ManualTrade.objects.create(user=self.user, symbol='AAPL',
                                                       total_amount=Decimal('100.00'))

    def test_manual_trade_view_set(self):
        response = self.client.get('/api/users/manual-trades/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['symbol'], 'AAPL')


class ComprehensiveTradeStatisticsViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='user1', email='user1@example.com', password='password')
        self.client.force_authenticate(user=self.user)
        self.trade_account = TradeAccount.objects.create(user=self.user, name='Test Account')
        self.manual_trade = ManualTrade.objects.create(user=self.user, symbol='AAPL',
                                                       total_amount=Decimal('100.00'))

    def test_comprehensive_trade_statistics_view(self):
        response = self.client.get('/api/users/statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('overall_statistics', response.data)
        self.assertIn('symbol_performances', response.data)
        self.assertIn('monthly_trade_summary', response.data)


class TradeAccountPerformanceViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='user1', email='user1@example.com', password='password')
        self.client.force_authenticate(user=self.user)
        self.trade_account = TradeAccount.objects.create(user=self.user, name='Test Account')
        self.manual_trade = ManualTrade.objects.create(user=self.user, symbol='AAPL',
                                                       total_amount=Decimal('100.00'))

    def test_trade_account_performance_view(self):
        response = self.client.get('/api/users/account-performance/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('account_performances', response.data)


class TradeNoteViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='user1', email='user1@example.com', password='password')
        self.client.force_authenticate(user=self.user)
        self.trade_note = TradeNote.objects.create(user=self.user, trade_note='Test Note')

    def test_trade_note_view_set(self):
        response = self.client.get('/api/users/trade-notes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class UserRegistrationViewTest(APITestCase):
    @patch('users.views.brevo_email_service.send_registration_email')
    def test_user_registration_view(self, mock_send_registration_email):
        mock_send_registration_email.return_value = (True, None)
        data = {
            'username': 'user2',
            'email': 'user2@example.com',
            'password': 'password'
        }
        response = self.client.post('/api/users/register/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)


class UserGetAllTradeAccountsViewTest(APITestCase):
    @patch('users.views.MetaApiService.fetch_accounts')
    def test_user_get_all_trade_accounts_view(self, mock_fetch_accounts):
        mock_fetch_accounts.return_value = []
        self.user = User.objects.create_user(username='user1', email='user1@example.com', password='password')
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/users/get_all_trades/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertIn('meta_trade_trades', response.data)
        self.assertIn('trade_locker_trades', response.data)


class LeaderBoardViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='user1', email='user1@example.com', password='password')
        self.client.force_authenticate(user=self.user)

    def test_leaderboard_view(self):
        response = self.client.get('/api/users/leaderboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)


class UserGetAllTradesViewTest(APITestCase):
    @patch('users.views.MetaApiService.fetch_trades')
    def test_user_get_all_trades_view(self, mock_fetch_trades):
        mock_fetch_trades.return_value = []
        self.user = User.objects.create_user(username='user1', email='user1@example.com', password='password')
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/users/get_all_trades/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertIn('meta_trade_trades', response.data)
        self.assertIn('trade_locker_trades', response.data)
