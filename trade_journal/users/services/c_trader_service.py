import requests
from django.conf import settings

from ..models import ManualTrade, TradeAccount, TradeType
import logging
from ejtraderCT import Ctrader


logger = logging.getLogger(__name__)


class CTraderService:

    @staticmethod
    def refresh_account(account: TradeAccount):
        # Fetch and update trades
        trades = CTraderService.fetch_trades_terminal(account.account_id)

        # If there's nothing to iterate over, return None
        if not trades:
            return

        CTraderService.update_trades(trades, account)

    @staticmethod
    def update_trades(trades, account, active=False):

        for trade in trades:
            trade_type = None

            if trade["side"] == "Sell":
                trade_type = TradeType.sell
            elif trade["side"] == "Buy":
                trade_type = TradeType.buy

            ManualTrade.objects.update_or_create(
                account=account,
                exchange_id=str(trade["position_id"]),
                defaults={
                    "trade_type": trade_type,
                    "symbol": trade["name"],
                    "quantity": trade["amount"],
                    "volume": trade["amount"],
                    "open_price": trade["price"],
                    "gain": trade["gain"],
                    "profit": trade["diff"],
                    "active": active,
                },
            )


    @staticmethod
    def _get_client(server, username, password):
        c_trader = Ctrader(server="h8.p.c-trader.cn", account=f"demo.${str(server).lower()}.${str(username).lower()}", password=password)

        status = c_trader.isconnected()
        
        if status:
            return c_trader
        else:
            raise Exception("Invalid credentials")

    @staticmethod
    def fetch_trades_terminal(account: TradeAccount):
        c_trader = CTraderService._get_client(account.server, account.account_id, account.password)

        return c_trader.positions()
    
    @staticmethod
    def authenticate_sync(server, username, password):

        c_trader = CTraderService._get_client(server, username, password)

        return username, c_trader.client["currency"]
