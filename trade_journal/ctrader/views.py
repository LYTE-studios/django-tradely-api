import requests
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from metatrade.utils import encrypt_password, decrypt_password, KEY
from rest_framework.views import APIView

from .services import CTraderService
from .models import CTraderAccount
from ejtraderCT import Ctrader


User = get_user_model()


class DeleteAccount(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        account_id = kwargs['account_id']

        if not account_id:
            return Response({'error': 'All fields are required: account_id.'},
                            status=status.HTTP_400_BAD_REQUEST)

        account = CTraderAccount.objects.get(id=account_id)

        account.delete()

        return Response({
            'message': 'Account deleted.'
        }, status=status.HTTP_200_OK)


class CTraderAccountViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def login(self, request):
        user = self.request.user
        sender_id = request.data.get('account')
        password = request.data.get('password')
        server = request.data.get('server')
        account_name = request.data.get('account_name')

        CTraderService.login(user, server, sender_id, password)

        # Authenticate and get tokens
        api = Ctrader(server, sender_id, password)
        status = api.isconnected()
        if status:
            CTraderAccount.objects.update_or_create(
                user=user,
                defaults={
                    'account': sender_id,
                    'server': server,
                    'password': encrypt_password(password),
                    'key_code': KEY,
                    'account_name': account_name
                }
            )

            return Response({
                'message': 'Login successful.',
                'account': sender_id,
                'server': server,
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid login credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
