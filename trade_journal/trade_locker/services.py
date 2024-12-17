# trade_locker/services.py

from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Optional, Tuple
from django.utils import timezone
from .models import TraderLockerAccount, OrderHistory
import requests

class TradeLockerService:
    def __init__(self):
        self._refresh_lock = asyncio.Lock()

    def _get_api_urls(self, demo_status: bool) -> Tuple[str, str]:
        """Get API URLs based on demo status"""
        base = 'demo' if demo_status else 'live'
        return (
            f'https://{base}.tradelocker.com/backend-api/trade/accounts',
            f'https://{base}.tradelocker.com/backend-api/auth/jwt/all-accounts'
        )

    def _refresh_access_token(self, refresh_token: str, demo_status: bool = True) -> Optional[str]:
        """Refresh access token for TradeLocker API"""
        refresh_url = f'https://{"demo" if demo_status else "live"}.tradelocker.com/backend-api/auth/jwt/refresh'
        
        try:
            response = requests.post(refresh_url, json={"refreshToken": refresh_token})
            if response.status_code == 201:
                return response.json().get('accessToken')
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error refreshing access token: {str(e)}")
            return None

    def _fetch_all_account_numbers(self, api_url: str, access_token: str) -> Optional[List[Dict]]:
        """Fetch all account numbers from TradeLocker API"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'accept': 'application/json'
        }
        try:
            response = requests.get(api_url, headers=headers)
            if response.status_code == 200:
                return response.json().get('accounts', [])
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching account numbers: {str(e)}")
            return None

    def _fetch_orders_history(self, api_url: str, access_token: str, acc_num: str) -> Optional[List]:
        """Fetch orders history for a specific account"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'accept': 'application/json',
            'accNum': str(acc_num)
        }
        try:
            response = requests.get(api_url, headers=headers)
            if response.status_code == 200:
                return response.json().get('d', {}).get('ordersHistory', [])
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching orders history: {str(e)}")
            return None

    def _process_orders_history(self, orders_history: List, acc_id: str, trader_locker_id: int) -> List[Dict]:
        """Process orders history and create OrderHistory objects"""
        trade_history = []
        order_history_objects = []

        for history in orders_history:
            trade_info = {
                'order_id': history[0],
                'amount': history[3],
                'instrument_id': history[1],
                'side': history[4],
                'market': history[5],
                'market_status': history[6],
                'position_id': history[16],
                'price': history[8]
            }
            order_history_objects.append(
                OrderHistory(
                    acc_id=acc_id,
                    trader_locker_id=trader_locker_id,
                    **trade_info
                )
            )
            trade_history.append(trade_info)

        # Bulk create the order history objects
        OrderHistory.objects.bulk_create(order_history_objects)
        return trade_history

    def refresh_account(self, account: TraderLockerAccount) -> List[Dict]:
        """Refresh trades for a single account"""
        api_url_base, api_url_accounts = self._get_api_urls(account.demo_status)
        access_token = self._refresh_access_token(account.refresh_token, account.demo_status)
        
        if not access_token:
            raise Exception(f"Failed to refresh access token for account {account.id}")

        account_numbers = self._fetch_all_account_numbers(api_url_accounts, access_token)
        if not account_numbers:
            raise Exception(f"Failed to fetch account numbers for account {account.id}")

        all_orders_history = []
        for acc in account_numbers:
            acc_num, acc_id = acc.get('accNum'), acc.get('id')
            api_url_orders_history = f'{api_url_base}/{acc_id}/ordersHistory'
            orders_history = self._fetch_orders_history(api_url_orders_history, access_token, acc_num)
            
            if orders_history:
                trade_history = self._process_orders_history(orders_history, acc_id, account.id)
                all_orders_history.extend(trade_history)

        return all_orders_history

    @staticmethod
    def fetch_accounts(user) -> List[Dict]:
        """Fetch all TradeLocker accounts for a user"""
        accounts = TraderLockerAccount.objects.filter(user=user)
        return [
            {
                'id': account.id,
                'account_name': account.account_name,
                'demo_status': account.demo_status,
                'email': account.email,
                # Add other relevant fields
            }
            for account in accounts
        ]

    @staticmethod
    def fetch_trades(user) -> List[Dict]:
        """Fetch all TradeLocker trades for a user"""
        trades = OrderHistory.objects.filter(trader_locker__user=user)
        return [
            {
                'id': trade.id,
                'order_id': trade.order_id,
                'amount': trade.amount,
                'instrument_id': trade.instrument_id,
                'side': trade.side,
                'market': trade.market,
                'market_status': trade.market_status,
                'position_id': trade.position_id,
                'price': trade.price,
                # Add other relevant fields
            }
            for trade in trades
        ]

    def refresh_all_accounts(self, user) -> List[Dict]:
        """Refresh all TradeLocker accounts for a user"""
        accounts = TraderLockerAccount.objects.filter(user=user)
        all_trades = []
        
        for account in accounts:
            try:
                trades = self.refresh_account(account)
                all_trades.extend(trades)
            except Exception as e:
                print(f"Error refreshing account {account.id}: {str(e)}")
                continue
                
        return all_trades

