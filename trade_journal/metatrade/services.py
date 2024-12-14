from datetime import datetime, timedelta
import asyncio
from functools import wraps
from contextvars import ContextVar
from asgiref.sync import async_to_sync, sync_to_async
from metaapi_cloud_sdk import MetaApi, MetaStats
from trade_journal.my_secrets import meta_api_key

import asyncio

from .models import MetaTraderAccount, Trade

def run_async(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(func(*args, **kwargs))
    return wrapper

class MetaApiService:

    @staticmethod
    async def refresh_caches(user):
        try:  
            accounts = await sync_to_async(MetaTraderAccount.objects.filter)(user=user)
        except Exception as e:
            print(f"Error fetching meta accounts: {str(e)}")
            return
        
        for account in accounts:
            if account.cached_at and account.cached_until and account.cached_until > datetime.now():
                continue
            
            try:
                api = MetaApi(meta_api_key)
                meta_stats = MetaStats(meta_api_key)
                meta_trades = await meta_stats.get_account_trades(account.account_id)

                for trade in meta_trades:
                    await sync_to_async(Trade.objects.update_or_create)(user=user,
                        account_id=account.account_id,
                        defaults={
                            'volume': trade['volume'],
                            'duration_in_minutes': trade['durationInMinutes'],
                            'profit': trade['profit'],
                            'gain': trade['gain'],
                            'success': trade['success'],
                            'type': trade['type'],
                            'open_time': trade['openTime'],
                        })
                    
                meta_account = await api.metatrader_account_api.get_account(account.account_id)
                connection = meta_account.get_rpc_connection()
                await connection.connect()
                account_information = await connection.get_account_information()
                await connection.close()
                await meta_account.undeploy()

                account.balance = account_information['balance']
                account.cached_until = datetime.now() + timedelta(minutes=30)
                account.cached_at = datetime.now()
                await sync_to_async(account.save)()

            except Exception as e:
                print(f"Error refreshing account: {str(e)}")
                continue
    
    @staticmethod
    def _refresh_caches_sync(user):
        """Synchronous wrapper for refresh_caches"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(MetaApiService.refresh_caches(user))
        except Exception as e:
            print(f"Error reloading cached meta accounts: {str(e)}")
        finally:
            loop.close()

    @staticmethod
    def fetch_accounts(user):
        """Synchronous method to fetch accounts"""
        accounts = MetaTraderAccount.objects.filter(user=user)
        account_list = list(accounts)  # Materialize the queryset
        
        # Run refresh_caches in a separate thread
        import threading
        def refresh():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(MetaApiService.refresh_caches(user))
            finally:
                loop.close()
        
        thread = threading.Thread(target=refresh)
        thread.start()
        thread.join(timeout=5)  # Wait up to 5 seconds

        return [account.to_dict() for account in account_list]

    @staticmethod
    def fetch_trades(user):
        """Synchronous method to fetch trades"""

        accounts = MetaTraderAccount.objects.filter(user=user)
        account_list = list(accounts)
        
        # Run refresh_caches in a separate thread
        import threading
        def refresh():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(MetaApiService.refresh_caches(user))
            finally:
                loop.close()
        
        thread = threading.Thread(target=refresh)
        thread.start()
        thread.join(timeout=5)  # Wait up to 5 seconds
        
        trades = Trade.objects.filter(account_id__in=[account.id for account in account_list])
        return [trade.to_dict() for trade in trades]