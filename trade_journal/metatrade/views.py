from asgiref.sync import async_to_sync, sync_to_async
from django.contrib.auth import get_user_model
from metaapi_cloud_sdk import MetaApi
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import asyncio
from functools import wraps

from .models import MetaTraderAccount
from .serializers import MetaTraderAccountSerializer
from .services import MetaApiService
from .utils import encrypt_password, KEY

import logging

logger = logging.getLogger(__name__)

User = get_user_model()

from trade_journal.my_secrets import meta_api_key


def with_event_loop(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(f(*args, **kwargs))

    return wrapper


class DeleteAccount(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @with_event_loop
    async def delete(self, request, *args, **kwargs):
        account_id = kwargs['account_id']

        if not account_id:
            return Response({'error': 'All fields are required: account_id.'},
                            status=status.HTTP_400_BAD_REQUEST)

        account = await sync_to_async(MetaTraderAccount.objects.get)(id=account_id)

        await sync_to_async(account.delete)()

        return Response({
            'message': 'Account deleted.'
        }, status=status.HTTP_200_OK)


class MetaTraderAccountViewSet(viewsets.ModelViewSet):
    serializer_class = MetaTraderAccountSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def login_account(self, request):
        server_name = request.data.get('server_name')
        account_name = request.data.get('account_name')
        username = request.data.get('username')
        password = request.data.get('password')
        platform = request.data.get('platform')

        async def connect_account(data: dict):
            api = MetaApi(meta_api_key)

            account = await api.metatrader_account_api.create_account(data)

            await account.wait_deployed()

            await account.create_replica({
                'region': 'new-york',
                'magic': 1000,
            })
            
            return account

        if not all([server_name, username, password, platform]):
            return Response(
                {'error': 'All fields are required: server_name, username, password, and platform.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create a new event loop for the async account creation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)  

        try:

            # Synchronous account creation
            account = loop.run_until_complete(
                connect_account({
                'type': 'cloud',
                'login': username,
                'name': account_name,
                'password': password,
                'server': server_name,
                'platform': platform,
                'metastatsApiEnabled': True,
                'magic': 1000,
            })
            )

        except Exception as meta_error:
            logger.error(f"MetaApi create_account failed: {str(meta_error)}")
            return Response(
                {'error': str(meta_error)},
                status=status.HTTP_400_BAD_REQUEST
            )
        finally:
            loop.close()

        user = request.user

        try:
            # Use standard Django ORM method
            trader_account, created = MetaTraderAccount.objects.update_or_create(
                account_id=account.id,
                defaults={
                    'user': user,
                    'email': username,
                    'password': encrypt_password(password),
                    'key_code': KEY,
                    'server': server_name,
                    'account_name': account_name,
                }
            )
            logger.info(f"{'Created' if created else 'Updated'} trader account: {trader_account.id}")

        except Exception as db_error:
            logger.error(f"Database operation failed: {str(db_error)}")
            return Response(
                {'error': 'Failed to save account information'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'message': 'Login successful.',
            'account_id': account.id,
            'email': username,
            'user_id': trader_account.user.id
        }, status=status.HTTP_200_OK)
