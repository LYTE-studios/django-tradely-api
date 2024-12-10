from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch
from .models import TraderLockerAccount
from django.contrib.auth import get_user_model

User = get_user_model()


class TraderLockerAccountViewSetTests(APITestCase):

    @patch('app_name.views.authenticate')  # Use the actual app name
    def test_login_success(self, mock_authenticate):
        mock_authenticate.return_value = ('mock_access_token', 'mock_refresh_token')

        user_data = {
            'email': 'test@example.com',
            'password': 'password',
            'server': 'server_name'
        }
        response = self.client.post(reverse('traderlockeraccount-login'), user_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'Login successful.')

        # Verify user and trader locker account creation
        user = User.objects.get(email='test@example.com')
        trader_account = TraderLockerAccount.objects.get(user=user)
        self.assertEqual(trader_account.email, 'test@example.com')
        self.assertEqual(trader_account.refresh_token, 'mock_refresh_token')

    @patch('app_name.views.authenticate')  # Use the actual app name
    def test_login_invalid_credentials(self, mock_authenticate):
        mock_authenticate.return_value = (None, None)

        user_data = {
            'email': 'test@example.com',
            'password': 'wrong_password',
            'server': 'server_name'
        }
        response = self.client.post(reverse('traderlockeraccount-login'), user_data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertContains(response, "Invalid credentials or server information.")


class FetchTradesViewTests(APITestCase):

    @patch('app_name.views.refresh_access_token')
    @patch('app_name.views.fetch_all_account_numbers')
    def test_fetch_trades_success(self, mock_fetch_all_account_numbers, mock_refresh_access_token):
        # Create a TraderLockerAccount
        user = User.objects.create(email='test@example.com')
        TraderLockerAccount.objects.create(
            user=user,
            email='test@example.com',
            refresh_token='mock_refresh_token'
        )

        mock_refresh_access_token.return_value = 'mock_access_token'
        mock_fetch_all_account_numbers.return_value = [{'accNum': '123', 'id': 'acc_id'}]

        response = self.client.post(reverse('fetchtrades-fetch_trades'), {'email': 'test@example.com'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @patch('app_name.views.refresh_access_token')
    def test_fetch_trades_account_does_not_exist(self, mock_refresh_access_token):
        mock_refresh_access_token.return_value = 'mock_access_token'

        response = self.client.post(reverse('fetchtrades-fetch_trades'), {'email': 'nonexistent@example.com'})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertContains(response, "Account does not exist for the given email.")

    @patch('app_name.views.refresh_access_token')
    def test_fetch_trades_refresh_token_invalid(self, mock_refresh_access_token):
        user = User.objects.create(email='test@example.com')
        TraderLockerAccount.objects.create(
            user=user,
            email='test@example.com',
            refresh_token='mock_refresh_token'
        )

        mock_refresh_access_token.return_value = None  # Simulate invalid refresh token

        response = self.client.post(reverse('fetchtrades-fetch_trades'), {'email': 'test@example.com'})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertContains(response, "Failed to refresh access token.")
