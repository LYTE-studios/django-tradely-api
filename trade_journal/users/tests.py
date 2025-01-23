from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from django.urls import reverse
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from .models import TradeAccount, ManualTrade, TradeNote, CustomUser
from .services import TradeService

User = get_user_model()

class TradeServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.trade_account = TradeAccount.objects.create(
            user=self.user,
            #name='Test Account',
            balance=Decimal('1000.00')
        )

    @patch('metatrade.services.MetaApiService')
    @patch('trade_locker.services.TradeLockerService')
    def test_get_all_trades(self, mock_trade_locker, mock_meta_api):
        mock_meta_api.fetch_trades.return_value = [
            {'id': 1, 'profit': 100, 'account_type': 'meta_api'}
        ]
        mock_trade_locker.fetch_trades.return_value = [
            {'id': 2, 'profit': 200, 'account_type': 'trade_locker'}
        ]

        trades = TradeService.get_all_trades(self.user)
        
        self.assertEqual(len(trades), 2)
        self.assertEqual(trades[0]['profit'], 100)
        self.assertEqual(trades[1]['profit'], 200)

    @patch('metatrade.services.MetaApiService')
    @patch('trade_locker.services.TradeLockerService')
    def test_get_all_accounts(self, mock_trade_locker, mock_meta_api):
        mock_meta_api.fetch_accounts.return_value = [
            {'id': 1, 'balance': 1000, 'type': 'meta_api'}
        ]
        mock_trade_locker.fetch_accounts.return_value = [
            {'id': 2, 'balance': 2000, 'type': 'trade_locker'}
        ]

        accounts = TradeService.get_all_accounts(self.user)
        
        self.assertEqual(accounts['total_balance'], Decimal('3000'))
        self.assertEqual(len(accounts['accounts']), 2)

class AccountViewsTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
    @patch('users.services.TradeService.get_all_accounts')
    def test_accounts_summary_view(self, mock_get_accounts):
        mock_get_accounts.return_value = {
            'total_balance': Decimal('3000'),
            'accounts': []
        }
        response = self.client.get(reverse('get-all-trade-accounts'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_balance'], '3000')

    @patch('users.services.TradeService.get_account_performance')
    def test_account_performance_view(self, mock_get_performance):
        mock_get_performance.return_value = {
            'total_profit': Decimal('500'),
            'total_trades': 10
        }

        response = self.client.get(reverse('trade-account-performance'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_profit'], '500')

# Keep the original authentication-related tests
class UserLoginViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', email='user1@example.com', password='password')

    def test_user_login_view(self):
        data = {
            'username': 'user1',
            'password': 'password'
        }
        response = self.client.post(reverse('login'), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_user_login_view_invalid_credentials(self):
        data = {
            'username': 'user1',
            'password': 'wrongpassword'
        }
        response = self.client.post(reverse('login'), data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], 'Invalid credentials')

class UserRegistrationViewTest(APITestCase):
    @patch('users.views.brevo_email_service.send_registration_email')
    def test_user_registration_view(self, mock_send_registration_email):
        mock_send_registration_email.return_value = (True, None)
        data = {
            'username': 'user2',
            'email': 'user2@example.com',
            'password': 'password'
        }
        response = self.client.post(reverse('register'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)


class TradeStatisticsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@test.com', password='testpass123')
        self.account = TradeAccount.objects.create(user=self.user, balance=Decimal('1000.00'))
        self.trade1 = ManualTrade.objects.create(account=self.account, gain=Decimal('0.03'), profit=Decimal('30'))  # Above threshold
        self.trade2 = ManualTrade.objects.create(account=self.account, gain=Decimal('0.01'), profit=Decimal('10'))  # Below threshold
        self.trade3 = ManualTrade.objects.create(account=self.account, gain=Decimal('-0.03'), profit=Decimal('-30'))  # Loss above threshold

    def test_trade_statistics_threshold(self):
        stats = TradeService.get_trade_statistics(self.user)  # Pass user to get statistics
        
        self.assertEqual(stats['total_trades'], 2)  # Only counts trades above threshold
        self.assertEqual(stats['winning_trades'], 1)
        self.assertEqual(stats['losing_trades'], 1)
        self.assertEqual(stats['trades_below_threshold'], 1)
        
        
class ToggleUserAccountStatusTests(APITestCase):
    def setUp(self):
        # Create a test user
        self.user = CustomUser.objects.create_user(username="testuser", password="testpassword")
        self.client = APIClient()

        # Create a trade account for the user
        self.trade_account = TradeAccount.objects.create(user=self.user, disabled=False)

        # Authenticate the user
        self.client.force_authenticate(user=self.user)

        # Base URL for the API with account_id as a parameter
        self.url = f"/api/users/toggle-account-mode/{self.trade_account.id}/"

    def test_disable_account(self):
        # Send a PATCH request with disable=True (account disabled)
        response = self.client.patch(self.url, {"disable": True}, format="json")

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["response"], "account disabled")
        self.trade_account.refresh_from_db()
        self.assertTrue(self.trade_account.disabled)

    def test_enable_account(self):
        # Disable the account first
        self.trade_account.disabled = True
        self.trade_account.save()

        response = self.client.patch(self.url, {"disable": False}, format="json")

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["response"], "account enabled")
        self.trade_account.refresh_from_db()
        self.assertFalse(self.trade_account.disabled)

    def test_invalid_disable_value(self):
        response = self.client.patch(self.url, {"disable": "invalid"}, format="json")

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "mode must be a boolean (true or false)")

    def test_account_does_not_exist(self):
        url = "/api/users/toggle-account-mode/99999/"
        response = self.client.patch(url, {"disable": True}, format="json")

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)
