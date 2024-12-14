from datetime import datetime, timezone
from rest_framework import status
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.test import APITestCase

from trade_locker.models import TraderLockerAccount

from .models import TradeAccount, ManualTrade, TradeNote

User = get_user_model()


class HelloThereViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='user1', email='user1@example.com', password='password')
        self.client.force_authenticate(user=self.user)

    def test_hello_there_view(self):
        response = self.client.get('/api/users/hello-there/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


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
        self.user = User.objects.create_user(
            username='user1', 
            email='user1@example.com', 
            password='password'
        )
        self.client.force_authenticate(user=self.user)
        self.trade_account = TradeAccount.objects.create(
            user=self.user, 
            name='Test Account'
        )
        self.manual_trade = ManualTrade.objects.create(
            account=self.trade_account,
            symbol='AAPL',
            total_amount=Decimal('100.00'),
            trade_type='BUY',
            quantity=1,
            price=Decimal('100.00')
        )

    def test_manual_trade_view_set(self):
        response = self.client.get('/api/users/manual-trades/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['symbol'], 'AAPL')

    def test_create_manual_trade(self):
        data = {
            'account': self.trade_account.id,
            'symbol': 'GOOGL',
            'trade_type': 'BUY',
            'quantity': 1,
            'price': '150.00'
        }
        response = self.client.post('/api/users/manual-trades/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ManualTrade.objects.count(), 2)

    def test_create_manual_trade_wrong_account(self):
        other_user = User.objects.create_user(
            username='user2', 
            email='user2@example.com', 
            password='password'
        )
        other_account = TradeAccount.objects.create(
            user=other_user, 
            name='Other Account'
        )
        data = {
            'account': other_account.id,
            'symbol': 'GOOGL',
            'trade_type': 'BUY',
            'quantity': 1,
            'price': '150.00'
        }
        response = self.client.post('/api/users/manual-trades/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class ComprehensiveTradeStatisticsViewTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='user1', 
            email='user1@example.com', 
            password='password'
        )
        self.client.force_authenticate(user=self.user)
        self.trade_account = TradeAccount.objects.create(
            user=self.user, 
            name='Test Account'
        )
        self.manual_trade = ManualTrade.objects.create(
            account=self.trade_account,
            symbol='AAPL',
            total_amount=Decimal('100.00'),
            trade_type='BUY',
            quantity=1,
            price=Decimal('100.00'),
            trade_date=datetime.now(timezone.utc)
        )

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
        self.manual_trade = ManualTrade.objects.create(
            account=self.trade_account, 
            symbol='AAPL',
            trade_type='BUY',
            quantity=1,
            price=Decimal('100.00')
        )
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

    @patch('users.views.MetaApiService.fetch_accounts')
    @patch('users.views.refresh_access_token')
    @patch('users.views.fetch_all_account_numbers')
    def test_user_get_all_trade_accounts_view(
        self, 
        mock_fetch_all_account_numbers, 
        mock_refresh_access_token, 
        mock_fetch_accounts
    ):
        # Setup mocks
        mock_fetch_accounts.return_value = []
        mock_refresh_access_token.return_value = 'mock_token'
        mock_fetch_all_account_numbers.return_value = []
        
        # Create user and authenticate
        self.user = User.objects.create_user(
            username='user1', 
            email='user1@example.com', 
            password='password'
        )
        self.client.force_authenticate(user=self.user)

        TraderLockerAccount.objects.create(
            user=self.user,
            email='test@example.com',
            refresh_token='test_token',
            server='test_server',
            account_name='test_account'
        )
        
        # Make request
        response = self.client.get('/api/users/get_all_accounts/')
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertIn('meta_trade_accounts', response.data)
        self.assertIn('trade_locker_accounts', response.data)
        
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
