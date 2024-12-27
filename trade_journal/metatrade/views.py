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

    @action(detail=False, methods=['post'])
    def login_account(self, request):
        server_name = request.data.get('server_name')
        account_name = request.data.get('account_name')
        username = request.data.get('username')
        password = request.data.get('password')
        platform = request.data.get('platform')

        if not all([server_name, username, password, platform]):
            return Response(
                {'error': 'All fields are required: server_name, username, password, and platform.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            account = MetaApiService.authenticate_sync(server_name, username, password, platform, account_name)

            user = request.user
            try:
                trader_account = MetaTraderAccount.objects.update_or_create(
                    account_id=account.id,
                    user=user,
                    defaults={
                        'email': username,
                        'password': encrypt_password(password),
                        'key_code': KEY,
                        'server': server_name,
                        'account_name': account_name,
                    }
                )
                logger.info(f"Created/Updated trader account: {trader_account[0].id}")

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
                'user_id': trader_account[0].user.id
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Unexpected error in login_account: {str(e)}")
            logger.exception(e)
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
