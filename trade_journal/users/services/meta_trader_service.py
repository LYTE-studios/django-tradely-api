import requests
from django.conf import settings

from ..models import ManualTrade, TradeAccount, TradeType
import logging

logger = logging.getLogger(__name__)


class MetaTraderService:

    @staticmethod
    def refresh_account(account: TradeAccount):
        # Fetch and update trades
        meta_trades = MetaTraderService.fetch_trades_terminal(account.account_id)

        # If there's nothing to iterate over, return None
        if not meta_trades:
            return

        MetaTraderService.update_trades(meta_trades, account)

    @staticmethod
    def update_trades(meta_trades, account, active=False):
        from django.utils.dateparse import parse_datetime
        from django.utils.timezone import is_aware, make_aware

        def get_aware_datetime(date_str):
            from datetime import datetime
            ret = datetime.fromtimestamp(date_str)
            if not is_aware(ret):
                ret = make_aware(ret)
            return ret

        for trade in meta_trades:
            if trade["type"] == 2:
                ManualTrade.objects.update_or_create(
                    account=account,
                    exchange_id=str(trade["position_id"]),
                    defaults={
                        "profit": trade["profit"],
                        "gain": 0,
                        "open_time": get_aware_datetime(trade["time"]),
                        "close_time": get_aware_datetime(trade["time"]),
                        "is_top_up": True,
                        "active": active,
                    },
                )
                continue
            else:
                trade_type = None

                if trade["type"] == 0:
                    trade_type = TradeType.sell
                elif trade["type"] == 1:
                    trade_type = TradeType.buy

                if trade["entry"] == 0:
                    ManualTrade.objects.update_or_create(
                        account=account,
                        exchange_id=str(trade["position_id"]),
                        defaults={
                            "trade_type": trade_type,
                            "symbol": trade["symbol"],
                            "quantity": trade["volume"],
                            "volume": trade["volume"],
                            "open_price": trade["price"],
                            "open_time": get_aware_datetime(trade["time"]),
                            "active": active,
                        },
                    )

                if trade["entry"] == 1:
                    ManualTrade.objects.update_or_create(
                        account=account,
                        exchange_id=str(trade["position_id"]),
                        defaults={
                            "trade_type": trade_type,
                            "symbol": trade["symbol"],
                            "quantity": trade["volume"],
                            "volume": trade["volume"],
                            "close_price": trade["price"],
                            "profit": trade["profit"],
                            "gain": 0,
                            "close_time": get_aware_datetime(trade["time"]),
                            "active": active,
                        },
                    )

    @staticmethod
    def fetch_trades_terminal(account_id: str):
        try:
            base_url = settings.TERMINAL_SERVER_URL
            response = requests.post(
                base_url + "/api/mt5/get_trades/", json={"account_id": account_id}
            )
            if response.status_code == 200:
                data = response.json()
                orders = data["orders"]
                return orders
            else:
                print(
                    f"Error fetching trades for account {account_id}: {response.text}"
                )
                return []
        except Exception as e:
            print(f"Error fetching trades for account {account_id}: {str(e)}")
            return []

    @staticmethod
    def authenticate_sync(server, username, password, platform) -> str:
        base_url = settings.TERMINAL_SERVER_URL
        response = requests.post(
            base_url + "/api/mt5/connect/",
            json={
                "account": username,
                "password": password,
                "server": server,
            },
        )
        if response.status_code == 200:
            data = response.json()
            if data["status"] == "success":
                account_info = data["account_info"]
                return account_info["login"], account_info["currency"]
        else:
            error = "{}: {}".format(str(response.status_code), response.json())
            logger.error(error)
            raise Exception(error)
