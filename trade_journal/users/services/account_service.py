import logging

from ..models import ManualTrade, TradeAccount

logger = logging.getLogger(__name__)
from django.utils import timezone
from ..models import Platform


class AccountService:

    @staticmethod
    def delete_account(account: TradeAccount):
        # Delete all trades associated with the account
        ManualTrade.objects.filter(account=account).delete()
        print(f"Deleted trades for account: {account.id}")

        account.delete()
        print(f"Deleted account: {account.id}")

    @staticmethod
    def calculate_account_balance(account: TradeAccount):
        trades = ManualTrade.objects.filter(account=account)
        return sum(trade.profit for trade in trades)

    @staticmethod
    def update_account_cache(account: TradeAccount):
        account.balance = AccountService.calculate_account_balance(account)

        account.cached_until = timezone.now() + timezone.timedelta(seconds=10)
        account.cached_at = timezone.now()

        account.save()

    @staticmethod
    def refresh_account(account: TradeAccount):
        from .meta_trader_service import MetaTraderService

        match account.platform:
            case Platform.meta_trader_4 | Platform.meta_trader_5:
                MetaTraderService.refresh_account(account)

        AccountService.update_account_cache(account)

    @staticmethod
    def check_refresh(user, force_refresh=False):
        def needs_refresh(account: TradeAccount) -> bool:
            if not account.cached_at or not account.cached_until:
                return True

            return account.cached_until <= timezone.now()

        accounts = TradeAccount.objects.filter(user=user)

        for account in accounts:
            if not force_refresh and not needs_refresh(account):
                continue

            AccountService.refresh_account(account)

    @staticmethod
    def authenticate(
        username, password, server, platform, account_name, user
    ) -> TradeAccount:

        account_id: str = None

        import json

        base_credentials = json.dumps(
            {
                "username": username,
                "password": password,
                "server": server,
                "platform": platform,
            }
        )

        try:
            existing_account = TradeAccount.objects.get(credentials=base_credentials)
        except TradeAccount.DoesNotExist:
            existing_account = None

        if existing_account:
            trade_account, created = TradeAccount.objects.update_or_create(
                account_id=existing_account.account_id,
                user=user,
                defaults={
                    "credentials": base_credentials,
                    "account_name": account_name,
                    "platform": platform,
                    "currency": existing_account.currency,
                },
            )
            return trade_account

        match platform:
            case Platform.meta_trader_4:
                from .meta_trader_service import MetaTraderService

                account_id, currency = MetaTraderService.authenticate_sync(
                    server, username, password, "mt4"
                )
            case Platform.meta_trader_5:
                from .meta_trader_service import MetaTraderService

                account_id, currency = MetaTraderService.authenticate_sync(
                    server, username, password, "mt5"
                )
            case Platform.c_trader:
                from .c_trader_service import CTraderService

                account_id, currency = CTraderService.authenticate_sync(
                    server, username, password
                )

        if not account_id:
            raise Exception("Something went wrong..")

        try:
            trade_account, created = TradeAccount.objects.update_or_create(
                account_id=account_id,
                user=user,
                defaults={
                    "account_name": account_name,
                    "platform": platform,
                    "currency": currency,
                    "server": server,
                    "password": password,
                },
            )

            print(f"Modified trader account: {trade_account.id}, created: {created}")

        except Exception as db_error:
            print(f"Database operation failed: {str(db_error)}")
            raise Exception("Failed to save account information")

        return trade_account
