import unittest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from .services import CTraderService
from .models import CTraderAccount, CTrade
from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from rest_framework import status

User = get_user_model()


class CTraderServiceTest(unittest.TestCase):

    @patch('ctrader.services.Ctrader')
    @patch('ctrader.services.CTraderAccount.objects.update_or_create')
    def test_login_account(self, mock_update_or_create, mock_ctrader):
        user = MagicMock(spec=User)
        server = 'test_server'
        sender_id = 'test_sender_id'
        password = 'test_password'

        mock_api = mock_ctrader.return_value
        mock_api.isconnected.return_value = True

        status = CTraderService.login_account(user, server, sender_id, password)

        self.assertTrue(status)
        mock_update_or_create.assert_called_once_with(
            user=user,
            defaults={
                'account': sender_id,
                'server': server,
                'password': unittest.mock.ANY,
                'key_code': unittest.mock.ANY,
            }
        )

    @patch('ctrader.services.CTraderAccount.objects.filter')
    def test_fetch_accounts(self, mock_filter):
        user = MagicMock(spec=User)
        mock_account = MagicMock()
        mock_account.id = 1
        mock_account.account_name = 'test_account'
        mock_account.demo_status = False
        mock_account.email = 'test@example.com'
        mock_filter.return_value = [mock_account]

        accounts = CTraderService.fetch_accounts(user)

        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0]['id'], 1)
        self.assertEqual(accounts[0]['account'], 'test_account')
        self.assertEqual(accounts[0]['demo_status'], False)
        self.assertEqual(accounts[0]['email'], 'test@example.com')

    @patch('ctrader.services.CTrade.objects.filter')
    def test_fetch_trades(self, mock_filter):
        user = MagicMock(spec=User)
        mock_trade = MagicMock()
        mock_trade.id = 1
        mock_trade.order_id = 'order_1'
        mock_trade.amount = 1000
        mock_trade.instrument_id = 'instrument_1'
        mock_trade.side = 'buy'
        mock_trade.market = 'market_1'
        mock_trade.market_status = 'open'
        mock_trade.position_id = 'position_1'
        mock_trade.price = 1.2345
        mock_filter.return_value = [mock_trade]

        trades = CTraderService.fetch_trades(user)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]['id'], 1)
        self.assertEqual(trades[0]['order_id'], 'order_1')
        self.assertEqual(trades[0]['amount'], 1000)
        self.assertEqual(trades[0]['instrument_id'], 'instrument_1')
        self.assertEqual(trades[0]['side'], 'buy')
        self.assertEqual(trades[0]['market'], 'market_1')
        self.assertEqual(trades[0]['market_status'], 'open')
        self.assertEqual(trades[0]['position_id'], 'position_1')
        self.assertEqual(trades[0]['price'], 1.2345)

    @patch('ctrader.services.Ctrader')
    @patch('ctrader.services.CTraderAccount.objects.filter')
    @patch('ctrader.services.CTrade.objects.update_or_create')
    @patch('ctrader.services.decrypt_password')
    def test_get_trades(self, mock_decrypt_password, mock_update_or_create, mock_filter, mock_ctrader):
        user = MagicMock(spec=User)
        mock_account = MagicMock()
        mock_account.server = 'test_server'
        mock_account.sender_id = 'test_sender_id'
        mock_account.password = 'encrypted_password'
        mock_account.key_code = 'key_code'
        mock_filter.return_value.first.return_value = mock_account

        mock_decrypt_password.return_value = 'decrypted_password'
        mock_api = mock_ctrader.return_value
        mock_api.isconnected.return_value = True
        mock_api.orders.return_value = [
            {
                'ord_id': 'order_1',
                'name': 'trade_1',
                'side': 'buy',
                'amount': 1000,
                'price': 1.2345,
                'actual_price': 1.2345,
                'pos_id': 'position_1',
                'clid': 'clid_1',
                'type': 'DEAL_TYPE_TRADE'
            }
        ]

        trades = CTraderService.get_trades(user)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]['ord_id'], 'order_1')
        mock_update_or_create.assert_called_once_with(
            user=user,
            ord_id='order_1',
            defaults={
                'name': 'trade_1',
                'side': 'buy',
                'amount': 1000,
                'price': 1.2345,
                'actual_price': 1.2345,
                'pos_id': 'position_1',
                'clid': 'clid_1',
            }
        )


class DeleteAccountTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.account = CTraderAccount.objects.create(
            user=self.user,
            account='test_account',
            server='test_server',
            password=b'encrypted_password',
            key_code=b'key_code'
        )

    @patch('ctrader.views.CTraderAccount.objects.get')
    def test_delete_account(self, mock_get):
        mock_get.return_value = self.account
        url = reverse('c_trader_delete-account', kwargs={'account_id': self.account.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Account deleted.')
        mock_get.return_value.delete.assert_called_once()

    def test_delete_account_missing_id(self):
        url = reverse('c_trader_delete-account', kwargs={'account_id': ''})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'All fields are required: account_id.')


class CTraderAccountViewSetTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch('ctrader.views.Ctrader')
    @patch('ctrader.views.CTraderAccount.objects.update_or_create')
    def test_login_success(self, mock_update_or_create, mock_ctrader):
        mock_api = mock_ctrader.return_value
        mock_api.isconnected.return_value = True

        url = reverse('c_trader_login')
        data = {
            'account': 'test_account',
            'password': 'test_password',
            'server': 'test_server',
            'demo_status': True,
            'account_name': 'test_account_name'
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Login successful.')
        self.assertEqual(response.data['account'], 'test_account')
        self.assertEqual(response.data['server'], 'test_server')
        mock_update_or_create.assert_called_once_with(
            user=self.user,
            defaults={
                'account': 'test_account',
                'server': 'test_server',
                'password': unittest.mock.ANY,
                'key_code': unittest.mock.ANY,
            }
        )

    @patch('ctrader.views.Ctrader')
    def test_login_invalid_credentials(self, mock_ctrader):
        mock_api = mock_ctrader.return_value
        mock_api.isconnected.return_value = False

        url = reverse('c_trader_login')
        data = {
            'account': 'test_account',
            'password': 'test_password',
            'server': 'test_server',
            'demo_status': True,
            'account_name': 'test_account_name'
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['error'], 'Invalid login credentials.')
