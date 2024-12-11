from rest_framework import generics, permissions, viewsets, status
from rest_framework_simplejwt.tokens import AccessToken
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    TradeAccountSerializer,
    ManualTradeSerializer,
    TradeNoteSerializer
)
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny
from .models import CustomUser, TradeAccount, ManualTrade, TradeNote
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal
from .email_service import brevo_email_service
from metatrade.models import MetaTraderAccount
from trade_locker.models import TraderLockerAccount, OrderHistory
from metaapi_cloud_sdk import MetaApi, MetaStats
from cryptography.fernet import Fernet
import asyncio
import requests
from rest_framework import status
from django.db import transaction
from concurrent.futures import ThreadPoolExecutor


class HelloThereView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]


class UserRegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()  # or your own user model
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]  # Allow public access


class UserLoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            token = AccessToken.for_user(user)
            return Response({'access': str(token)})
        return Response({'detail': 'Invalid credentials'}, status=401)


class BaseModelViewSet(viewsets.ModelViewSet):
    """
    Enhanced base ViewSet with consistent response formatting
    """

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = self.perform_create(serializer)

            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({
                'success': False,
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return Response({
                'success': True,
                'data': serializer.data
            })
        except ValidationError as e:
            return Response({
                'success': False,
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response({
                'success': True,
                'message': 'Object successfully deleted'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'errors': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class TradeAccountViewSet(BaseModelViewSet):
    serializer_class = TradeAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TradeAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)


class ManualTradeViewSet(BaseModelViewSet):
    serializer_class = ManualTradeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Fetch only trades from accounts owned by the current user
        return ManualTrade.objects.filter(account__user=self.request.user)

    def perform_create(self, serializer):
        # Validate that the account belongs to the current user
        account_id = serializer.validated_data.get('account')
        if not TradeAccount.objects.filter(id=account_id.id, user=self.request.user).exists():
            raise ValidationError("You can only add trades to your own accounts.")

        return serializer.save(user=self.request.user)


class ComprehensiveTradeStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get user's trades
        trades = ManualTrade.objects.filter(user=request.user)

        # Overall statistics
        overall_statistics = {
            'total_trades': trades.count(),
            'total_invested': sum(trade.total_amount for trade in trades)
        }

        # Symbol performances
        symbol_performances = {}
        for trade in trades:
            if trade.symbol not in symbol_performances:
                symbol_performances[trade.symbol] = {
                    'symbol': trade.symbol,
                    'total_trades': 0,
                    'total_amount': Decimal('0')
                }
            symbol_performances[trade.symbol]['total_trades'] += 1
            symbol_performances[trade.symbol]['total_amount'] += trade.total_amount

        # Monthly trade summary (simplified)
        monthly_trade_summary = {}
        for trade in trades:
            month_key = trade.trade_date.strftime('%Y-%m')
            if month_key not in monthly_trade_summary:
                monthly_trade_summary[month_key] = {
                    'month': month_key,
                    'total_trades': 0,
                    'total_amount': Decimal('0')
                }
            monthly_trade_summary[month_key]['total_trades'] += 1
            monthly_trade_summary[month_key]['total_amount'] += trade.total_amount

        return Response({
            'overall_statistics': overall_statistics,
            'symbol_performances': list(symbol_performances.values()),
            'monthly_trade_summary': list(monthly_trade_summary.values())
        })


class TradeAccountPerformanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get user's trade accounts
        accounts = TradeAccount.objects.filter(user=request.user)

        account_performances = []
        for account in accounts:
            # Get trades for this specific account
            trades = ManualTrade.objects.filter(user=request.user, account=account)

            account_performance = {
                'account_id': account.id,
                'account_name': account.name,
                'total_trades': trades.count(),
                'total_traded_amount': sum(trade.total_amount for trade in trades),
                'current_balance': account.balance
            }
            account_performances.append(account_performance)

        return Response({
            'account_performances': account_performances
        })


class TradeNoteViewSet(viewsets.ModelViewSet):
    queryset = TradeNote.objects.all()
    serializer_class = TradeNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TradeNote.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)


class UserRegistrationView(APIView):
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Send registration email
            try:
                success, _ = brevo_email_service.send_registration_email(
                    user_email=user.email,
                    username=user.username
                )
                if not success:
                    # Log email sending failure but don't block registration
                    logger.warning(f"Failed to send registration email to {user.email}")
            except Exception as e:
                logger.error(f"Email service error: {e}")

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def fetch_all_account_numbers(api_url, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'accept': 'application/json'
    }
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            return response.json().get('accounts', [])
        else:
            return None
    except requests.exceptions.RequestException as e:
        return None


def refresh_access_token(refresh_token, demo_status=True):
    if demo_status:
        refresh_url = 'https://demo.tradelocker.com/backend-api/auth/jwt/refresh'
    else:
        refresh_url = 'https://live.tradelocker.com/backend-api/auth/jwt/refresh'
    payload = {
        "refreshToken": refresh_token
    }
    try:
        response = requests.post(refresh_url, json=payload)
        if response.status_code == 201:
            auth_data = response.json()
            return auth_data.get('accessToken', None)
        else:
            return None
    except requests.exceptions.RequestException as e:
        return None


def fetch_orders_history(api_url_orders_history, access_token, acc_num):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'accept': 'application/json',
        'accNum': str(acc_num)
    }
    try:
        response = requests.get(api_url_orders_history, headers=headers)
        if response.status_code == 200:
            return response.json().get('d', {}).get('ordersHistory', [])
        else:
            return None
    except requests.exceptions.RequestException as e:
        return None


# Function to fetch instruments available for trading
def fetch_account_instruments(api_url_base, access_token, acc_num, locale='en'):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'accept': 'application/json',
        'accNum': str(acc_num)
    }
    params = {
        'locale': locale
    }
    try:
        response = requests.get(api_url_base, headers=headers, params=params)
        if response.status_code == 200:
            return response.json().get('d', {}).get('instruments', [])
        else:
            return None
    except requests.exceptions.RequestException as e:
        return None


class UserGetAllTradeAccountsView(APIView):

    async def meta_api_synchronization(self, meta_account):
        token = meta_account.api_token
        login = meta_account.email
        temp_password = meta_account.password
        key_code = meta_account.key_code
        cipher = Fernet(key_code)
        password = cipher.decrypt(temp_password.encode()).decode()
        server_name = meta_account.server
        api = MetaApi(token)
        try:
            # Add test MetaTrader account
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
                        'login': login,
                        'password': password,
                        'server': server_name,
                        'platform': 'mt4',
                        'magic': 1000,
                    }
                )
            else:
                print('MT4 account already added to MetaApi')

            await account.deploy()
            await account.wait_connected()

            # connect to MetaApi API
            connection = account.get_rpc_connection()
            await connection.connect()
            terminal_state = await connection.wait_synchronized()
            #
            account_information = terminal_state.get_account_information()
            await connection.close()
            await account.undeploy()
            return account_information

        except Exception as err:
            # process errors
            if hasattr(err, 'details'):
                # returned if the server file for the specified server name has not been found
                # recommended to check the server name or create the account using a provisioning profile
                if err.details == 'E_SRV_NOT_FOUND':
                    print(err)
                # returned if the server has failed to connect to the broker using your credentials
                # recommended to check your login and password
                elif err.details == 'E_AUTH':
                    print(err)
                # returned if the server has failed to detect the broker settings
                # recommended to try again later or create the account using a provisioning profile
                elif err.details == 'E_SERVER_TIMEZONE':
                    print(err)
            print(api.format_error(err))
        exit()

    def get(self, request):
        try:
            user_data = {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
            }
            meta_trade_accounts = MetaTraderAccount.objects.filter(user=request.user)
            trade_locker_accounts = TraderLockerAccount.objects.filter(user=request.user)
            meta_account_info_list = []
            trade_account_info_list = []
            for meta_account in meta_trade_accounts:
                account_info = asyncio.run(self.meta_api_synchronization(meta_account))
                meta_account_info_list.append(account_info)

            for trade_account in trade_locker_accounts:
                refresh_token = trade_account.refresh_token
                demo_status = trade_account.demo_status
                if demo_status:
                    api_url_accounts = 'https://demo.tradelocker.com/backend-api/auth/jwt/all-accounts'
                else:
                    api_url_accounts = 'https://live.tradelocker.com/backend-api/auth/jwt/all-accounts'
                access_token = refresh_access_token(refresh_token)

                account_numbers = fetch_all_account_numbers(api_url_accounts, access_token)
                for account in account_numbers:
                    trade_account_info_list.append(account)

            # Build a response structure
            response_data = {
                'user': user_data,
                'meta_trade_accounts': meta_account_info_list,
                'trade_locker_accounts': trade_account_info_list
            }

            return Response(response_data, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class UserGetAllTradesView(APIView):
    def get(self, request):
        try:
            user_data = self.get_user_data(request.user)
            meta_trade_accounts = MetaTraderAccount.objects.filter(user=request.user)
            trade_locker_accounts = TraderLockerAccount.objects.filter(user=request.user)

            with ThreadPoolExecutor() as executor:
                meta_trade_futures = [executor.submit(self.fetch_meta_trades, account) for account in
                                      meta_trade_accounts]
                trade_locker_futures = [executor.submit(self.fetch_trade_locker_data, account) for account in
                                        trade_locker_accounts]

                meta_trade_list = [future.result() for future in meta_trade_futures]
                trade_locker_list = [future.result() for future in trade_locker_futures]

            response_data = {
                'user': user_data,
                'meta_trade_accounts': meta_trade_list,
                'trade_locker_accounts': trade_locker_list
            }

            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_user_data(self, user):
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        }

    def fetch_meta_trades(self, meta_account):
        api_token = meta_account.api_token
        return asyncio.run(self.connect_and_fetch_trades(api_token))

    async def connect_and_fetch_trades(self, api_token):
        api = MetaApi(api_token)
        meta_stats = MetaStats(api_token)
        try:
            accounts = await api.metatrader_account_api.get_accounts_with_infinite_scroll_pagination()
            account = next((item for item in accounts if item.type.startswith('cloud')), None)
            if not account:
                return "Account does not exist or is not of type cloud"

            if account.state != 'DEPLOYED':
                await account.deploy()

            if account.connection_status != 'CONNECTED':
                await account.wait_connected()

            return await meta_stats.get_account_open_trades(account.id)
        except Exception as e:
            return str(e)

    def fetch_trade_locker_data(self, trade_account):
        try:
            api_url_base, api_url_accounts = self.get_api_urls(trade_account.demo_status)
            access_token = refresh_access_token(trade_account.refresh_token)
            account_numbers = fetch_all_account_numbers(api_url_accounts, access_token)

            if not account_numbers:
                return f"Failed to fetch account numbers for user {trade_account.email}"

            return self.process_accounts(trade_account, account_numbers, api_url_base, access_token)
        except Exception as e:
            return str(e)

    def get_api_urls(self, demo_status):
        base = 'demo' if demo_status else 'live'
        return (
            f'https://{base}.tradelocker.com/backend-api/trade/accounts',
            f'https://{base}.tradelocker.com/backend-api/auth/jwt/all-accounts'
        )

    def process_accounts(self, trader_account, account_numbers, api_url_base, access_token):
        all_orders_history = []
        for account in account_numbers:
            acc_num, acc_id = account.get('accNum'), account.get('id')
            api_url_orders_history = f'{api_url_base}/{acc_id}/ordersHistory'
            orders_history = fetch_orders_history(api_url_orders_history, access_token, acc_num)
            if orders_history:
                trade_history = self.process_orders_history(orders_history, acc_id, trader_account.id)
                all_orders_history.extend(trade_history)
        return all_orders_history

    @transaction.atomic
    def process_orders_history(self, orders_history, acc_id, trader_locker_id):
        trade_history = []
        order_history_objects = []

        for history in orders_history:
            trade_info = {
                'order_id': history[0],
                'amount': history[3],
                'instrument_id': history[1],
                'side': history[4],
                'market': history[5],
                'market_status': history[6],
                'position_id': history[16],
                'price': history[8]
            }
            order_history_objects.append(
                OrderHistory(
                    acc_id=acc_id,
                    trader_locker_id=trader_locker_id,
                    **trade_info
                )
            )
            trade_history.append(trade_info)

        OrderHistory.objects.bulk_create(order_history_objects)
        return trade_history
