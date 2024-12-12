from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response

from .services import MetaApiService
from .models import MetaTraderAccount, Trade
from .serializers import MetaTraderAccountSerializer
from metaapi_cloud_sdk import MetaApi, MetaStats
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .utils import encrypt_password, KEY
from datetime import datetime, timedelta
from asgiref.sync import async_to_sync
import asyncio

User = get_user_model()

from trade_journal.my_secrets import meta_api_key

class DeleteAccount(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        account_id = kwargs['account_id']

        if not account_id:
            return Response({'error': 'All fields are required: account_id.'},
                            status=status.HTTP_400_BAD_REQUEST)

        account = MetaTraderAccount.objects.get(id=account_id)

        account.delete()

        return Response({
            'message': 'Account deleted.'
        }, status=status.HTTP_200_OK)

class MetaTraderAccountViewSet(viewsets.ModelViewSet):
    serializer_class = MetaTraderAccountSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def login_account(self, request):
        server_name = request.data.get('server_name')
        username = request.data.get('username')
        password = request.data.get('password')
        account_name = request.data.get('account_name')
        platform = request.data.get('platform')

        if not server_name or not username or not password:
            return Response({'error': 'All fields are required: server_name, username, and password.'},
                            status=status.HTTP_400_BAD_REQUEST)

        async def connect_metatrade_login():
            api = MetaApi(meta_api_key)
            try:
                try:    
                    account = await api.metatrader_account_api.create_account(
                        {
                            'name': account_name,
                            'type': 'cloud',
                            'login': username,
                            'password': password,
                            'server': server_name,
                            'platform': platform,
                            'magic': 1000,
                        }
                    )

                    return account
                except Exception as e:
                    return str(e)

            except Exception as e:
                return str(e)

        account = asyncio.run(connect_metatrade_login())

        if isinstance(account, str):
            return Response({'error': account}, status=status.HTTP_400_BAD_REQUEST)

        # Here you would typically process and save the trades to your database
        # For this example, we're just returning them
        user = request.user
        trader_account, created = MetaTraderAccount.objects.update_or_create(
            user=user,
            defaults={
                'account_id': account.id,
                'email': username,
                'password': encrypt_password(password),
                'key_code': KEY,
                'server': server_name,
                'account_name': account_name,
            }
        )

        MetaApiService._refresh_caches(user=user)

        return Response({
            'message': 'Login successful.',
            'account_id': account.id,
            'email': username,
            'user_id': trader_account.user.id
        }, status=status.HTTP_200_OK)

