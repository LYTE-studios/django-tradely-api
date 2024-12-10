from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import MetaTraderAccount, Trade
from .serializers import MetaTraderAccountSerializer
from metaapi_cloud_sdk import MetaApi, MetaStats
import asyncio
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from .utils import encrypt_password, decrypt_password, KEY

User = get_user_model()


class MetaTraderAccountViewSet(viewsets.ModelViewSet):
    serializer_class = MetaTraderAccountSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def login_account(self, request):
        api_token = request.data.get('api_token')
        server_name = request.data.get('server_name')
        username = request.data.get('username')
        password = request.data.get('password')

        if not api_token or not server_name or not username or not password:
            return Response({'error': 'All fields are required: api_token, server_name, username, and password.'},
                            status=status.HTTP_400_BAD_REQUEST)

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
                    try:
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
                    except Exception as e:
                        return str(e)
                else:
                    return account

            except Exception as e:
                return str(e)

        login_status = asyncio.run(connect_metatrade_login())

        if isinstance(login_status, str):
            return Response({'error': login_status}, status=status.HTTP_400_BAD_REQUEST)

        # Here you would typically process and save the trades to your database
        # For this example, we're just returning them
        user = request.user
        trader_account, created = MetaTraderAccount.objects.update_or_create(
            user=user,
            defaults={
                'api_token': api_token,
                'email': username,
                'password': encrypt_password(password),
                'key_code': KEY,
                'server': server_name,
            }
        )
        return Response({
            'message': 'Login successful.',
            'api_token': api_token,
            'email': username,
            'user_id': trader_account.user.id
        }, status=status.HTTP_200_OK)


class FetchTradesView(viewsets.ModelViewSet):
    serializer_class = MetaTraderAccountSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def fetch_trades(self, request, pk=None):

        # Get the user's trader locker account
        try:
            email = request.data.get('email')
            trader_account = MetaTraderAccount.objects.get(email=email)
            api_token = trader_account.api_token
        except MetaTraderAccount.DoesNotExist:
            return Response({'error': "Account does not exist for the given email."}, status=status.HTTP_404_NOT_FOUND)

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
                open_trades = await meta_stats.get_account_open_trades(account.id)
                user_id = request.user.id
                for trade in open_trades:
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
