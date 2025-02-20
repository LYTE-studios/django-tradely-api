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
            ret = parse_datetime(date_str)
            if not is_aware(ret):
                ret = make_aware(ret)
            return ret

        for trade in meta_trades:
            if trade["type"] == "DEAL_TYPE_BALANCE":
                ManualTrade.objects.update_or_create(
                    account=account,
                    exchange_id=str(trade["_id"]).split("+")[1],
                    defaults={
                        "profit": trade["profit"],
                        "gain": 0,
                        "open_time": get_aware_datetime(trade["openTime"]),
                        "close_time": get_aware_datetime(trade["openTime"]),
                        "is_top_up": True,
                        "active": active,
                    },
                )
            else:
                trade_type = None

                if trade["type"] == "DEAL_TYPE_SELL":
                    trade_type = TradeType.sell
                elif trade["type"] == "DEAL_TYPE_BUY":
                    trade_type = TradeType.buy
                # if open trade
                if trade["type"] == "POSITION_TYPE_SELL":
                    trade_type = TradeType.sell
                elif trade["type"] == "POSITION_TYPE_BUY":
                    trade_type = TradeType.buy

                close_time = trade.get("closeTime", None)
                if close_time is not None:
                    close_time = get_aware_datetime(trade["closeTime"])
                ManualTrade.objects.update_or_create(
                    account=account,
                    exchange_id=str(trade["_id"]).split("+")[1],
                    defaults={
                        "trade_type": trade_type,
                        "symbol": trade["symbol"],
                        "quantity": trade["volume"],
                        "open_price": trade["openPrice"],
                        "close_price": trade.get("closePrice", None),
                        "profit": trade["profit"],
                        "gain": trade["gain"],
                        "duration_in_minutes": trade["durationInMinutes"],
                        "open_time": get_aware_datetime(trade["openTime"]),
                        "close_time": close_time,
                        "active": active,
                        "volume": trade["volume"],
                        "pips": trade.get("pips", None),
                        "risk_in_balance_percent": trade.get(
                            "riskInBalancePercent", None
                        ),
                        "risk_in_pips": trade.get("riskInPips", None),
                        "market_value": trade["marketValue"],
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
