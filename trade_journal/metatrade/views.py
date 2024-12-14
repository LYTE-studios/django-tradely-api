from asgiref.sync import async_to_sync, sync_to_async
from django.contrib.auth import get_user_model
from metaapi_cloud_sdk import MetaApi
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MetaTraderAccount
from .serializers import MetaTraderAccountSerializer
from .services import MetaApiService
from .utils import encrypt_password, KEY

import logging

logger = logging.getLogger(__name__)

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

    @action(detail=False, methods=['post'])
    def login_account(self, request):  # Make the view async
        server_name = request.data.get('server_name')
        username = request.data.get('username')
        password = request.data.get('password')
        platform = request.data.get('platform')

        if not all([server_name, username, password, platform]):
            return Response(
                {'error': 'All fields are required: server_name, username, password, and platform.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            api = MetaApi(meta_api_key)
            logger.info(f"Attempting to create MetaApi account for {username} on {server_name}")
            
            try:
                account = async_to_sync(api.metatrader_account_api.create_account)({
                        'type': 'cloud',
                        'login': username,
                        'password': password,
                        'server': server_name,
                        'platform': platform,
                        'magic': 1000,
                    })
                
                logger.info(f"Successfully created MetaApi account: {account.id}")
                
            except Exception as meta_error:
                logger.error(f"MetaApi create_account failed: {str(meta_error)}")
                logger.error(f"Full Error Object: {vars(meta_error)}")
                return Response(
                    {'error': str(meta_error)},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = request.user
            try:
                trader_account, created = MetaTraderAccount.objects.update_or_create(
                    user=user,
                    defaults={
                        'account_id': account.id,
                        'email': username,
                        'password': encrypt_password(password),
                        'key_code': KEY,
                        'server': server_name,
                        'account_name': account.name,
                    }
                )
                logger.info(f"Created/Updated trader account: {trader_account.id}")
                
            except Exception as db_error:
                logger.error(f"Database operation failed: {str(db_error)}")
                return Response(
                    {'error': 'Failed to save account information'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            try:
                async_to_sync(MetaApiService.refresh_caches)(user=user)
                logger.info("Successfully refreshed caches")
            except Exception as cache_error:
                logger.warning(f"Cache refresh failed (non-critical): {str(cache_error)}")

            return Response({
                'message': 'Login successful.',
                'account_id': account.id,
                'email': username,
                'user_id': trader_account.user.id
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Unexpected error in login_account: {str(e)}")
            logger.exception(e)
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
