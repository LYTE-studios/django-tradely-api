from ..decorators import ensure_event_loop
from ..models import ManualTrade
import logging
logger = logging.getLogger(__name__)
import asyncio
from datetime import datetime, timedelta

from metaapi_cloud_sdk import MetaApi, MetaStats
from trade_journal.my_secrets import meta_api_key
import uuid
from asgiref.sync import sync_to_async

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
            await self.update_trades(meta_trades, account.account_id)

            # await connection.close()
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
        
    async def update_trades(self, meta_trades, account_id):
        for trade in meta_trades:
            if trade['type'] == 'DEAL_TYPE_BALANCE':
                await sync_to_async(ManualTrade.objects.update_or_create)(
                    account_id=account_id,
                    exchange_id=str(trade['_id']).split('+')[1],
                    defaults={
                        'profit': trade['profit'],
                        'gain': 0,
                        'open_time': trade['openTime'],
                        'close_time': trade['openTime'],
                        'is_top_up': True,
                    }
                )
            else:
                trade_type = None

                if trade['type'] == 'DEAL_TYPE_SELL':
                    trade_type = 'SELL'
                elif trade['type'] == 'DEAL_TYPE_BUY':
                    trade_type = 'BUY'

                await sync_to_async(ManualTrade.objects.update_or_create)(
                    account_id=account_id,
                    trade_id=str(trade['_id']).split('+')[1],
                    defaults={
                        'trade_type': trade_type,
                        'symbol': trade['symbol'],
                        'quantity': trade['volume'],
                        'open_price': trade['openPrice'],
                        'close_price': trade['closePrice'],
                        'profit': trade['profit'],
                        'gain': trade['gain'],
                        'duration_in_minutes': trade['durationInMinutes'],
                        'open_time': trade['openTime'],
                        'close_time': trade['closeTime'],
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

            return account.id

        except Exception as meta_error:
            print(f"MetaApi create_account failed: {str(meta_error)}")
            print(f"Full Error Object: {vars(meta_error)}")

            raise meta_error

    @staticmethod
    @ensure_event_loop
    def authenticate_sync(server, username, password, platform , loop=None):
        return loop.run_until_complete(MetaTraderService.authenticate(server, username, password, platform))
