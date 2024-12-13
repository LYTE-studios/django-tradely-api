from datetime import datetime, timedelta

from asgiref.sync import async_to_sync
from metaapi_cloud_sdk import MetaApi, MetaStats
from trade_journal.my_secrets import meta_api_key

from .models import MetaTraderAccount, Trade


class MetaApiService:

    @staticmethod
    async def _refresh_caches(user):
        async def async_refresh():
            accounts = MetaTraderAccount.objects.filter(user=user)

            for account in accounts:
                if account.cached_at is not None and account.cached_until is not None:
                    if account.cached_until < datetime.now():
                        continue

                api = MetaApi(meta_api_key)
                meta_stats = MetaStats(meta_api_key)
                meta_trades = await meta_stats.get_account_trades(account.account_id)

                for trade in meta_trades:
                    Trade.objects.update_or_create(
                        user=user,
                        account_id=account.account_id,
                        defaults={
                            'volume': trade['volume'],
                            'duration_in_minutes': trade['durationInMinutes'],
                            'profit': trade['profit'],
                            'gain': trade['gain'],
                            'success': trade['success'],
                            'type': trade['type'],
                            'open_time': trade['openTime'],
                        }
                    )

                meta_account = await api.metatrader_account_api.get_account(account.account_id)
                connection = meta_account.get_rpc_connection()
                await connection.connect()
                account_information = await connection.get_account_information()
                await connection.close()
                await meta_account.undeploy()

                account.balance = account_information['balance']
                account.cached_until = datetime.now() + timedelta(minutes=30)
                account.cached_at = datetime.now()
                account.save()

        # Run the async function synchronously
        async_to_sync(async_refresh)()

    @staticmethod
    def fetch_accounts(user):
        MetaApiService._refresh_caches(user=user)

        accounts = MetaTraderAccount.objects.filter(user=user)

        return [account.to_dict() for account in accounts]

    @staticmethod
    def fetch_trades(user):
        MetaApiService._refresh_caches(user=user)

        accounts = MetaTraderAccount.objects.filter(user=user)

        trades = Trade.objects.filter(account_id__in=[account.id for account in accounts])

        return [trade.to_dict() for trade in trades]
