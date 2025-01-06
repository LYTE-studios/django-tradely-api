import asyncio
import logging
import logging
from functools import wraps
from datetime import datetime, timedelta
from datetime import datetime, timedelta
from typing import Optional
from django.utils import timezone
from asgiref.sync import async_to_sync, sync_to_async
from metaapi_cloud_sdk import MetaApi, MetaStats
from trade_journal.my_secrets import meta_api_key
from users.models import ManualTrade
from .models import MetaTraderAccount, Trade
import httpx
import httpx

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, cache_duration: int = 30):
        self.cache_duration = cache_duration
        self._refresh_lock = asyncio.Lock()

    def needs_refresh(self, cached_at: Optional[datetime], cached_until: Optional[datetime]) -> bool:
        if not cached_at or not cached_until:
            return True
        return cached_until <= timezone.now()

def ensure_event_loop(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return func(*args, **kwargs, loop=loop)
    return wrapper

class MetaApiService:
    def __init__(self):
        self.cache_manager = CacheManager()
        self._meta_api = None
        self._refresh_lock = asyncio.Lock()

    async def get_meta_api(self):
        if not self._meta_api:
            self._meta_api = MetaApi(meta_api_key)
        return self._meta_api

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
            logger.error(f"Timeout while fetching trades for account {account_id}")
            return []
        except Exception as e:
            logger.error(f"Error fetching trades for account {account_id}: {str(e)}")
            return []

    async def fetch_account_information(self, auth_token, account_id):
        url = f"https://mt-client-api-v1.new-york.agiliumtrade.ai/users/current/accounts/{account_id}/account-information"
        headers = {
            "Auth-Token": f"{auth_token}"
        }
        params = {
            "refreshTerminalState": "true"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response.json()

    async def fetch_account_information(self, auth_token, account_id):
        url = f"https://mt-client-api-v1.new-york.agiliumtrade.ai/users/current/accounts/{account_id}/account-information"
        headers = {
            "Auth-Token": f"{auth_token}"
        }
        params = {
            "refreshTerminalState": "true"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response.json()

    async def refresh_account(self, account, user):
        try:
            meta_api = await self.get_meta_api()
            meta_account = await meta_api.metatrader_account_api.get_account(account.account_id)

            await meta_account.deploy()
            await meta_account.wait_deployed()

            # Fetch and update trades
            meta_trades = await self.get_meta_trades(account.account_id)
            await self.update_trades(meta_trades, user, account.account_id)

            # Update account information
            account_information = await self.fetch_account_information(meta_api_key, account.account_id)

            # await connection.close()
            await meta_account.undeploy()

            # Update account cache
            await self.update_account_cache(account, account_information['balance'])

        except Exception as e:
            logger.error(f"Error refreshing account {account.account_id}: {str(e)}")
            logger.error(f"Error refreshing account {account.account_id}: {str(e)}")
            raise

    async def update_trades(self, meta_trades, user, account_id):
        for trade in meta_trades:
            if trade['type'] == 'DEAL_TYPE_BALANCE':
                continue
            await sync_to_async(Trade.objects.update_or_create)(
                user=user,
                account_id=account_id,
                trade_id=str(trade['_id']).split('+')[1],
                defaults={
                    'volume': trade['volume'],
                    'symbol': trade['symbol'],
                    'duration_in_minutes': trade['durationInMinutes'],
                    'profit': trade['profit'],
                    'gain': trade['gain'],
                    'success': trade['success'],
                    'type': trade['type'],
                    'open_time': trade['openTime'],
                    'close_time': trade['closeTime'],
                }
            )

    async def update_account_cache(self, account, balance):
        account.balance = balance
        account.cached_until = timezone.now() + timedelta(minutes=30)
        account.cached_at = timezone.now()
        await sync_to_async(account.save)()

    async def refresh_caches(self, user, force_refresh=False):
        async with self._refresh_lock:
            accounts = await sync_to_async(MetaTraderAccount.objects.filter)(user=user)
            async for account in accounts:
                if not force_refresh and not self.cache_manager.needs_refresh(
                        account.cached_at, account.cached_until
                ):
                    continue
                await self.refresh_account(account, user)

    @staticmethod
    def refresh_caches_sync(user, force_refresh=False):
        """
        Synchronous method that waits for cache refresh to complete
        """
        service = MetaApiService()

        try:
            async_to_sync(service.refresh_caches)(user, force_refresh=force_refresh)
        except Exception as e:
            logger.error(f"Error in refresh_caches_sync: {str(e)}")
            raise

    @staticmethod
    @ensure_event_loop
    def fetch_accounts(user, loop=None):
        service = MetaApiService()
        accounts = MetaTraderAccount.objects.filter(user=user)
        account_list = list(accounts)

        loop.create_task(service.refresh_caches(user))
        return [account.to_dict() for account in account_list]

    @staticmethod
    @ensure_event_loop
    def fetch_trades(user,from_time: datetime = None, to_time: datetime = None, loop=None):
        service = MetaApiService()
        accounts = MetaTraderAccount.objects.filter(user=user)
        account_list = list(accounts)

        loop.create_task(service.refresh_caches(user))

        if from_time and to_time:
            trades = Trade.objects.filter(account_id__in=[account.account_id for account in account_list], close_time__range=(from_time, to_time))      
        else:
            trades = Trade.objects.filter(account_id__in=[account.account_id for account in account_list])
        
        return [ManualTrade.from_metatrade(trade) for trade in trades]
    
    @staticmethod
    @ensure_event_loop
    def authenticate_sync(server, username, password, platform, account_name, loop=None):
        service = MetaApiService()

        account = loop.run_until_complete(service.authenticate(server, username, password, platform, account_name))

        return account
    
    async def authenticate(self, server, username, password, platform, account_name):
        try:
            api = MetaApi(meta_api_key)

            account = await api.metatrader_account_api.create_account({
                'type': 'cloud',
                'login': username,
                'name': account_name,
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

            logger.info(f"Successfully created MetaApi account: {account.id}")

            return account

        except Exception as meta_error:
            logger.error(f"MetaApi create_account failed: {str(meta_error)}")
            logger.error(f"Full Error Object: {vars(meta_error)}")

            raise meta_error
