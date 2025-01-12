
from ..models import ManualTrade, TradeAccount, Platform
import asyncio
import logging
logger = logging.getLogger(__name__)
from django.utils import timezone
from ..decorators import ensure_event_loop
from asgiref.sync import sync_to_async
from ..models import Platform

class AccountService:

    @staticmethod
    def delete_account(account: TradeAccount):
        account.delete()
        print(f"Deleted account: {account.id}")

        # Delete all trades associated with the account
        ManualTrade.objects.filter(account=account).delete()
        print(f"Deleted trades for account: {account.id}")

    @staticmethod
    def calculate_account_balance(account: TradeAccount):
        trades = ManualTrade.objects.filter(account=account)
        return sum(trade.profit for trade in trades)

    @staticmethod
    def update_account_cache(account: TradeAccount):
        account.balance = AccountService.calculate_account_balance(account)

        account.cached_until = timezone.now() + timezone.timedelta(minutes=30)
        account.cached_at = timezone.now()

        account.save()

    @staticmethod
    async def refresh_account(account: TradeAccount):
        from .meta_trader_service import MetaTraderService

        match account.platform:
            case Platform.meta_trader_4 | Platform.meta_trader_5:
                await MetaTraderService().refresh_account(account)

        sync_to_async(AccountService.update_account_cache)(account)

    @staticmethod
    async def check_refresh(user, force_refresh=False):
        def needs_refresh(account: TradeAccount) -> bool:
            if not account.cached_at or not account.cached_until:
                return True
            return account.cached_until <= timezone.now()
        
        _refresh_lock = asyncio.Lock()

        async with _refresh_lock:
            accounts = await sync_to_async(TradeAccount.objects.filter)(user=user)
            async for account in accounts:
                if not force_refresh and not needs_refresh(
                        account.cached_at, account.cached_until
                ):
                    continue
                await AccountService.refresh_account(account)

    @staticmethod
    @ensure_event_loop
    def cache_account_force(user, loop=None):
        loop.run_until_complete(AccountService.check_refresh(user, True))

    @staticmethod
    @ensure_event_loop
    def cache_account_task(user, loop=None):
        loop.create_task(AccountService.check_refresh(user, False))

    @staticmethod
    def authenticate(username, password, server, platform, account_name, user) -> TradeAccount:

        account_id : str = None 

        try:
            match platform:
                case Platform.meta_trader_4:
                    from .meta_trader_service import MetaTraderService
                    account_id =  MetaTraderService.authenticate_sync(server, username, password, 'mt4')
                case Platform.meta_trader_5:
                    from .meta_trader_service import MetaTraderService
                    account_id =  MetaTraderService.authenticate_sync(server, username, password, 'mt5')
        except Exception as e:
            print(f"Error authenticating account: {str(e)}") 
            raise Exception(f'Failed to authenticate accoun: {str(e)}t')

        if not account_id:
            raise Exception('Account not found')

        try:
            trade_account, created = TradeAccount.objects.update_or_create(
                account_id=account_id,
                user=user,
                defaults={
                    'account_name': account_name,
                    'status': 'active',
                    'platform': platform,
                }
            )

            print(f"Modified trader account: {trade_account.id}, created: {created}")

        except Exception as db_error:
            print(f"Database operation failed: {str(db_error)}")
            raise Exception('Failed to save account information')
        
        return trade_account
    