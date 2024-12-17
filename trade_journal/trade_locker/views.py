import requests
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import OrderHistory, Instruments
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import TraderLockerAccount  # Make sure to include the model
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from metatrade.utils import encrypt_password, decrypt_password, KEY
from rest_framework.views import APIView

User = get_user_model()


class DeleteAccount(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        account_id = kwargs['account_id']

        if not account_id:
            return Response({'error': 'All fields are required: account_id.'},
                            status=status.HTTP_400_BAD_REQUEST)

        account = TraderLockerAccount.objects.get(id=account_id)

        account.delete

        return Response({
            'message': 'Account deleted.'
        }, status=status.HTTP_200_OK)


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
        account_name = request.data.get('account_name')

        # Authenticate and get tokens
        access_token, refresh_token = authenticate(email, password, server, demo_status)

        if not access_token:
            return Response({'error': "Invalid credentials or server information."},
                            status=status.HTTP_401_UNAUTHORIZED)

        # Get or create a TraderLockerAccount linked to the user
        # user, created = User.objects.get_or_create(email=email)  # Or get user by email and handle accordingly
        user = request.user
        trader_account, created = TraderLockerAccount.objects.update_or_create(
            user=user,
            defaults={
                'email': email,
                'password': encrypt_password(password),
                'key_code': KEY,
                'refresh_token': refresh_token,
                'server': server,
                'demo_status': demo_status,
                'account_name': account_name,
            }
        )

        return Response({
            'message': 'Login successful.',
            'refresh_token': refresh_token,
            'email': trader_account.email,
            'user_id': trader_account.user.id,
            'demo_status': trader_account.demo_status,
        }, status=status.HTTP_200_OK)
