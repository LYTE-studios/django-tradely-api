from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
from users.models import CustomUser
from .models import TraderLockerAccount
from .services import TradeLockerService

class TradeLockerServiceTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.trade_locker_account = TraderLockerAccount.objects.create(
            user=self.user,
            email='test@test.com',
            refresh_token='test_token',
            demo_status=True
        )

    @patch('trade_locker.services.TradeLockerService._refresh_access_token')
    def test_refresh_account(self, mock_refresh_token):
        mock_refresh_token.return_value = 'new_access_token'

        service = TradeLockerService()
        result = service.refresh_account(self.trade_locker_account)
        
        self.assertTrue(result['success'])
        mock_refresh_token.assert_called_once_with(
            self.trade_locker_account.refresh_token,
            self.trade_locker_account.demo_status
        )

    @patch('trade_locker.services.TradeLockerService.fetch_orders_history')
    def test_fetch_trades(self, mock_fetch_orders):
        mock_fetch_orders.return_value = [
            {
                'order_id': '123',
                'amount': 100,
                'profit': 50
            }
        ]

        trades = TradeLockerService.fetch_trades(self.user)
        
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]['order_id'], '123')

class TradeLockerViewsTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.trade_locker_account = TraderLockerAccount.objects.create(
            user=self.user,
            email='test@test.com',
            refresh_token='test_token',
            demo_status=True
        )

    @patch('trade_locker.views.TradeLockerService.refresh_all_accounts')
    def test_refresh_accounts(self, mock_refresh):
        mock_refresh.return_value = {'success': True}
        response = self.client.post(reverse('refresh-trade-locker-accounts'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
