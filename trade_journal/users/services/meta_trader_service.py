from ..models import ManualTrade, TradeAccount, TradeType
import logging

logger = logging.getLogger(__name__)
import asyncio
from datetime import datetime, timedelta

from metaapi_cloud_sdk import MetaApi, MetaStats
from trade_journal.my_secrets import meta_api_key
import uuid
from asgiref.sync import sync_to_async, async_to_sync


class MetaTraderService:

    def __init__(self):
        self._meta_api = None

    async def get_meta_api(self):
        if not self._meta_api:
            self._meta_api = MetaApi(meta_api_key)
        return self._meta_api

    async def refresh_account(self, account):
        try:
            meta_api = await self.get_meta_api()
            meta_account = await meta_api.metatrader_account_api.get_account(account.account_id)

            await meta_account.deploy()
            await meta_account.wait_deployed()

            # Fetch and update trades
            meta_trades = await self.get_meta_trades(account.account_id)

            await self.update_trades(meta_trades, account)
            # get current open trade
            meta_open_trades = await self.get_meta_open_trades(account.account_id)

            await self.update_trades(meta_open_trades, account, True)

            await meta_account.undeploy()

        except Exception as e:
            print(f"Error refreshing account {account.account_id}: {str(e)}")
            raise

    async def get_meta_trades(self, account_id: str):
        meta_stats = MetaStats(meta_api_key, {
            'requestTimeout': 60000,
            'retryOpts': {
                'retries': 3,
                'minDelayInMilliseconds': 1000,
                'maxDelayInMilliseconds': 3000
            }
        })

        try:
            return await asyncio.wait_for(
                meta_stats.get_account_trades(
                    account_id,
                    start_time=datetime.now() - timedelta(days=365),
                    end_time=datetime.now() + timedelta(days=365)
                ),
                timeout=30
            )
        except asyncio.TimeoutError:
            print(f"Timeout while fetching trades for account {account_id}")
            return []
        except Exception as e:
            print(f"Error fetching trades for account {account_id}: {str(e)}")
            return []


    async def get_meta_open_trades(self, account_id: str):
        meta_stats = MetaStats(meta_api_key, {
            'requestTimeout': 60000,
            'retryOpts': {
                'retries': 3,
                'minDelayInMilliseconds': 1000,
                'maxDelayInMilliseconds': 3000
            }
        })

        try:
            return await asyncio.wait_for(
                meta_stats.get_account_open_trades(
                    account_id
                ),
                timeout=30
            )
        except asyncio.TimeoutError:
            print(f"Timeout while fetching trades for account {account_id}")
            return []
        except Exception as e:
            print(f"Error fetching trades for account {account_id}: {str(e)}")
            return []

    async def update_trades(self, meta_trades, account, active=False):

        from django.utils.dateparse import parse_datetime
        from django.utils.timezone import is_aware, make_aware

        def get_aware_datetime(date_str):
            ret = parse_datetime(date_str)
            if not is_aware(ret):
                ret = make_aware(ret)
            return ret

        for trade in meta_trades:
            if trade['type'] == 'DEAL_TYPE_BALANCE':
                await sync_to_async(ManualTrade.objects.update_or_create)(
                    account=account,
                    exchange_id=str(trade['_id']).split('+')[1],
                    defaults={
                        'profit': trade['profit'],
                        'gain': 0,
                        'open_time': get_aware_datetime(trade['openTime']),
                        'close_time': get_aware_datetime(trade['openTime']),
                        'is_top_up': True,
                        'active': active
                    }
                )
            else:
                trade_type = None

                if trade['type'] == 'DEAL_TYPE_SELL':
                    trade_type = TradeType.sell
                elif trade['type'] == 'DEAL_TYPE_BUY':
                    trade_type = TradeType.buy
                close_time = trade.get('closeTime', None)
                if close_time is not None:
                    close_time = get_aware_datetime(trade['closeTime'])
                await sync_to_async(ManualTrade.objects.update_or_create)(
                    account=account,
                    exchange_id=str(trade['_id']).split('+')[1],
                    defaults={
                        'trade_type': trade_type,
                        'symbol': trade['symbol'],
                        'quantity': trade['volume'],
                        'open_price': trade['openPrice'],
                        'close_price': trade.get('closePrice', None),
                        'profit': trade['profit'],
                        'gain': trade['gain'],
                        'duration_in_minutes': trade['durationInMinutes'],
                        'open_time': get_aware_datetime(trade['openTime']),
                        'close_time': close_time,
                        'active':  active
                    }
                )

    @staticmethod
    async def authenticate(server, username, password, platform) -> str:
        try:
            api = MetaApi(meta_api_key)

            account = await api.metatrader_account_api.create_account({
                'type': 'cloud',
                'login': username,
                'name': uuid.uuid4().hex,
                'password': password,
                'server': server,
                'platform': platform,
                'magic': 1000,
            })

            await account.wait_deployed()

            await account.enable_metastats_api()

            await account.create_replica({
                'region': 'new-york',
                'magic': 1000,
            })

            print(f"Successfully created MetaApi account: {account.id}")

            return account.id, account.base_currency

        except Exception as meta_error:
            print(f"MetaApi create_account failed: {str(meta_error)}")
            print(f"Full Error Object: {vars(meta_error)}")

            raise meta_error

    @staticmethod
    def authenticate_sync(server, username, password, platform):
        return async_to_sync(MetaTraderService.authenticate)(server, username, password, platform)
