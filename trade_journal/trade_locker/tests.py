from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import TraderLockerAccount

User = get_user_model()

class TraderLockerAccountViewSetTests(APITestCase):
    def setUp(self): 
        self.user = User.objects.create_user(username='user1', email='tanguy@lytestudios.be', password='!8fX5vOF')
        self.client.force_authenticate(user=self.user)

    correct_user_data = {
        'email': 'tanguy@lytestudios.be',
        'password': '!8fX5vOF',
        'server': 'OSP-DEMO',
        'account_name': 'test_account',
        'demo_status': True,
    }

    @patch('trade_locker.views.authenticate')
    def test_login_success(self, mock_authenticate):
        mock_authenticate.return_value = ('mock_access_token', 'mock_refresh_token')
        user_data = self.correct_user_data

        response = self.client.post(reverse('locker_login'), user_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Login successful.')

        # Verify user and trader locker account creation
        user = User.objects.get(email='tanguy@lytestudios.be')
        trader_account = TraderLockerAccount.objects.get(user=user)
        self.assertEqual(trader_account.email, 'tanguy@lytestudios.be')
        self.assertEqual(trader_account.refresh_token, 'mock_refresh_token')

    @patch('trade_locker.views.authenticate')
    def test_login_invalid_credentials(self, mock_authenticate):
        mock_authenticate.return_value = (None, None)
        user_data = self.correct_user_data
        
        response = self.client.post(reverse('locker_login'), user_data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['error'], "Invalid credentials or server information.")


class FetchTradesViewTests(APITestCase):
    def setUp(self): 
        self.user = User.objects.create_user(username='user1', email='tanguy@lytestudios.be', password='!8fX5vOF')
        self.client.force_authenticate(user=self.user)

    @patch('trade_locker.views.refresh_access_token')
    @patch('trade_locker.views.fetch_all_account_numbers')
    @patch('trade_locker.views.fetch_orders_history')
    def test_fetch_trades_success(self, mock_fetch_orders_history, mock_fetch_all_account_numbers, mock_refresh_access_token):
        user = User.objects.create(email='test@example.com')
        TraderLockerAccount.objects.create(
            user=user,
            email='test@example.com',
            refresh_token='mock_refresh_token'
        )

        mock_refresh_access_token.return_value = 'mock_access_token'
        mock_fetch_all_account_numbers.return_value = [{'accNum': '123', 'id': 'acc_id'}]
        mock_fetch_orders_history.return_value = []  # Or add some mock order data if needed

        response = self.client.post(reverse('fetch_trades'), {'email': 'test@example.com'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('email', response.data)
        self.assertIn('orders_history', response.data)

    @patch('trade_locker.views.refresh_access_token')
    def test_fetch_trades_account_does_not_exist(self, mock_refresh_access_token):
        mock_refresh_access_token.return_value = 'mock_access_token'

        response = self.client.post(reverse('fetch_trades'), {'email': 'nonexistent@example.com'})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['detail'], "No TraderLockerAccount matches the given query.")  # Updated error message
    @patch('trade_locker.views.refresh_access_token')
    def test_fetch_trades_refresh_token_invalid(self, mock_refresh_access_token):
        user = User.objects.create(email='test@example.com')
        TraderLockerAccount.objects.create(
            user=user,
            email='test@example.com',
            refresh_token='mock_refresh_token'
        )

        mock_refresh_access_token.return_value = None  # Simulate invalid refresh token

        response = self.client.post(reverse('fetch_trades'), {'email': 'test@example.com'})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['error'], "Failed to refresh access token.")
