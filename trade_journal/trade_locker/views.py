import requests
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import OrderHistory, Instruments
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import TraderLockerAccount  # Make sure to include the model
from django.contrib.auth import get_user_model

User = get_user_model()


# Create your views here.
def authenticate(email, password, server, demo_status=True):
    if demo_status:
        auth_url = 'https://demo.tradelocker.com/backend-api/auth/jwt/token'
    else:
        auth_url = 'https://live.tradelocker.com/backend-api/auth/jwt/token'
    payload = {
        "email": email,
        "password": password,
        "server": server
    }
    try:
        response = requests.post(auth_url, json=payload)
        if response.status_code == 201:
            auth_data = response.json()
            return auth_data.get('accessToken', None), auth_data.get('refreshToken', None)
        else:
            return None, None
    except requests.exceptions.RequestException as e:
        return None, None


# Function to fetch all account numbers using JWT access token
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


# Function to fetch orders history for a specific account using JWT access token and account number
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


class TraderLockerAccountViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def login(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        server = request.data.get('server')
        demo_status = request.data.get('demo_status', True)

        # Authenticate and get tokens
        access_token, refresh_token = authenticate(email, password, server, demo_status)

        if not access_token:
            return Response({'error': "Invalid credentials or server information."},
                            status=status.HTTP_401_UNAUTHORIZED)

        # Get or create a TraderLockerAccount linked to the user
        user, created = User.objects.get_or_create(email=email)  # Or get user by email and handle accordingly
        trader_account, created = TraderLockerAccount.objects.update_or_create(
            user=user,
            defaults={
                'email': email,
                'refresh_token': refresh_token,
                'server': server,
                'demo_status': demo_status,
            }
        )

        return Response({
            'message': 'Login successful.',
            'refresh_token': refresh_token,
            'email': trader_account.email,
            'user_id': trader_account.user.id,
            'demo_status': trader_account.demo_status,
        }, status=status.HTTP_200_OK)


class FetchTradesView(viewsets.ModelViewSet):
    permission_classes = [AllowAny]

    @action(detail=True, methods=['post'])
    def fetch_trades(self, request):

        email = request.data.get('email')
        # Get the user's trader locker account
        try:
            trader_account = TraderLockerAccount.objects.get(email=email)
            refresh_token = trader_account.refresh_token
            demo_status = trader_account.demo_status
            if demo_status:
                api_url_base = 'https://demo.tradelocker.com/backend-api/trade/accounts'
                api_url_accounts = 'https://demo.tradelocker.com/backend-api/auth/jwt/all-accounts'
            else:
                api_url_base = 'https://live.tradelocker.com/backend-api/trade/accounts'
                api_url_accounts = 'https://live.tradelocker.com/backend-api/auth/jwt/all-accounts'
        except TraderLockerAccount.DoesNotExist:
            return Response({'error': "Account does not exist for the given email."}, status=status.HTTP_404_NOT_FOUND)
        result_data = []

        # Refresh the access token using the refresh token
        access_token = refresh_access_token(refresh_token)

        # Fetch all account numbers
        account_numbers = fetch_all_account_numbers(api_url_accounts, access_token)
        if not account_numbers:
            return Response({'error': f"Failed to fetch account numbers for user {email}. Skipping to next user"},
                            status=status.HTTP_401_UNAUTHORIZED)

        user_results = {
            'email': email,
            'account_numbers': []
        }

        for account in account_numbers:
            acc_num = account.get('accNum')
            acc_id = account.get('id')

            # Fetch orders history for the account
            api_url_orders_history_base = f'{api_url_base}/{acc_id}/ordersHistory'
            orders_history = fetch_orders_history(api_url_orders_history_base, access_token, acc_num)
            if orders_history:
                for history in orders_history:
                    # Save each order history into the OrderHistory model
                    OrderHistory.objects.create(
                        acc_id=acc_id,
                        history=history  # Assuming 'history' contains the details you want to store
                    )

            # Fetch instruments available for trading
            api_url_instruments_base = f'{api_url_base}/{acc_id}/instruments'
            account_instruments = fetch_account_instruments(api_url_instruments_base, access_token, acc_num)
            if account_instruments:
                instruments_list = []
                for instrument in account_instruments:
                    # Save each instrument into the Instruments model
                    inst, created = Instruments.objects.get_or_create(
                        tradableInstrumentId=instrument.get('tradableInstrumentId'),
                        defaults={
                            'name': instrument.get('name'),
                            'description': instrument.get('description'),
                            'type': instrument.get('type'),
                            'tradingExchange': instrument.get('tradingExchange'),
                            'country': instrument.get('country'),
                            'logoUrl': instrument.get('logoUrl'),
                            'localizedName': instrument.get('localizedName'),
                            'routes': instrument.get('routes'),
                            'barSource': instrument.get('barSource'),
                            'hasIntraday': instrument.get('hasIntraday'),
                            'hasDaily': instrument.get('hasDaily'),
                        }
                    )
                    instruments_list.append(inst)

                user_results['account_numbers'].append({
                    'acc_num': acc_num,
                    'acc_id': acc_id,
                    'instruments': [inst.name for inst in instruments_list]  # List of instrument names
                })

        result_data.append(user_results)
        return Response(result_data, status=status.HTTP_200_OK)
