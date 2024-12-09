from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import MetaTraderAccount, Trade
from .serializers import MetaTraderAccountSerializer
from metaapi_cloud_sdk import MetaApi, MetaStats
import asyncio
from rest_framework.permissions import AllowAny


class MetaTraderAccountViewSet(viewsets.ModelViewSet):
    serializer_class = MetaTraderAccountSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=['post'])
    def login_account(self, request):
        username = request.GET.get('username')
        password = request.GET.get('password')
        server_name = request.GET.get('server_name')
        api_token = request.GET.get('api_token')

        async def connect_metatrade_login():
            api = MetaApi(api_token)
            try:
                accounts = await api.metatrader_account_api.get_accounts_with_infinite_scroll_pagination()
                account = None
                for item in accounts:
                    if item.type.startswith('cloud'):
                        account = item
                        break

                if not account:
                    print('Adding MT4 account to MetaApi')
                    account = await api.metatrader_account_api.create_account(
                        {
                            'name': 'Test account',
                            'type': 'cloud',
                            'login': username,
                            'password': password,
                            'server': server_name,
                            'platform': 'mt4',
                            'magic': 1000,
                        }
                    )
                    return account
                else:
                    print('MT4 account already added to MetaApi')
                    return account

            except Exception as e:
                return str(e)

        login_status = asyncio.run(connect_metatrade_login())

        if isinstance(login_status, str):
            return Response({'error': login_status}, status=status.HTTP_400_BAD_REQUEST)

        # Here you would typically process and save the trades to your database
        # For this example, we're just returning them
        return Response(login_status)


class FetchTradesView(viewsets.ModelViewSet):
    serializer_class = MetaTraderAccountSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def fetch_trades(self, request, pk=None):

        api_token = request.GET.get('api_token')
        account_id = request.GET.get('account_id')

        async def connect_and_fetch_trades():
            api = MetaApi(api_token)
            meta_stats = MetaStats(api_token)
            accounts = await api.metatrader_account_api.get_accounts_with_infinite_scroll_pagination()
            account = None
            for item in accounts:
                if item.type.startswith('cloud'):
                    account = item
                    break
            if not account:
                return "account does not exist or is not of type cloud"
            if account.state != 'DEPLOYED':
                await account.deploy()
            else:
                print('Account already deployed')
            print('Waiting for API server to connect to broker (may take couple of minutes)')
            if account.connection_status != 'CONNECTED':
                await account.wait_connected()
            try:
                open_trades = await meta_stats.get_account_open_trades(account_id)
                user_id = request.user.id
                for trade in open_trades['trades']:
                    # Extract trade details
                    trade_instance = Trade(
                        user_id=user_id,
                        trade_id=trade['tradeId'],
                        symbol=trade['symbol'],
                        volume=trade['volume'],
                        price_open=trade['openPrice'],
                        price_close=trade['closePrice'],
                        profit=trade['profit'],
                        create_time=trade['openTime'],
                        close_time=trade['closeTime']
                    )
                    trade_instance.save()  # Save to your database
                return trades
            except Exception as e:
                return str(e)

        trades = asyncio.run(connect_and_fetch_trades())

        if isinstance(trades, str):
            return Response({'error': trades}, status=status.HTTP_400_BAD_REQUEST)

        # Here you would typically process and save the trades to your database
        # For this example, we're just returning them
        return Response(trades)
