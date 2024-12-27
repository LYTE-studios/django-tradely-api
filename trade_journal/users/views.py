from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from datetime import datetime
import requests
from django.utils import timezone
from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Sum
from metatrade.models import Trade
from metatrade.services import MetaApiService
from rest_framework import permissions, viewsets, generics
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken
from trade_locker.models import TraderLockerAccount, OrderHistory
from .services import TradeService

from .email_service import brevo_email_service
from .models import CustomUser, TradeAccount, ManualTrade, TradeNote
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    TradeAccountSerializer,
    ManualTradeSerializer,
    TradeNoteSerializer
)


class HelloThereView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({'message': 'Hello There!'})


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
        # Get trades from accounts owned by the current user
        return ManualTrade.objects.filter(account__user=self.request.user)

    def perform_create(self, serializer):
        # Ensure the account belongs to the current user
        account = serializer.validated_data.get('account')
        if not account.user == self.request.user:
            raise ValidationError("You can only add trades to your own accounts.")
        serializer.save()

class TradeNoteViewSet(viewsets.ModelViewSet):
    queryset = TradeNote.objects.all()
    serializer_class = TradeNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Base queryset filtered by user
        queryset = TradeNote.objects.filter(user=self.request.user)
        
        # Check if date parameter is provided in the request
        date_param = self.request.query_params.get('date', None)
        if date_param:
            try:
                # Convert the date string to a date object
                date = timezone.datetime.strptime(date_param, '%Y-%m-%d').date()
                # Filter queryset by the specific date
                queryset = queryset.filter(note_date=date)
            except ValueError:
                # Handle invalid date format
                return TradeNote.objects.none()
        
        return queryset

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
                    print(f"Failed to send registration email to {user.email}")
            except Exception as e:
                print(f"Email service error: {e}")

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AccountsSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            accounts_summary = TradeService.get_all_accounts(request.user)
            return Response(accounts_summary, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Error fetching accounts: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AccountPerformanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            performance = TradeService.get_account_performance(request.user)
            return Response(performance, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Error fetching account performance: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ComprehensiveTradeStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        trades = TradeService.get_all_trades(request.user)
        statistics = TradeService.calculate_statistics(trades)
        return Response(statistics)

class LeaderBoardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        leaderboard = TradeService.get_leaderboard()
        return Response(leaderboard)

class RefreshAllAccountsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        force_refresh = request.data.get('force_refresh', True)
        
        try:
            refresh_summary = TradeService.refresh_all_accounts(
                request.user, 
                force_refresh=force_refresh
            )
            
            return Response({
                'message': 'Refresh complete',
                'summary': refresh_summary
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class UserGetAllTradesView(APIView):
    def get(self, request):
        
        try:            
            
            from_date = request.query_params.get('from')
            until_date = request.query_params.get('to')

            # Parse datetime parameters
            parsed_from_date = None
            parsed_until_date = None

            if from_date:
                parsed_from_date = timezone.datetime.strptime(from_date, '%Y-%m-%d')

            if until_date:
                parsed_until_date = timezone.datetime.strptime(until_date, '%Y-%m-%d')

            # Fetch trades using the service method with optional datetime filtering
            trades = TradeService.get_all_trades(
                request.user, 
                from_date=parsed_from_date, 
                to_date=parsed_until_date
            )
            
            response_data = {
                'user': {
                    "id": request.user.id,
                    "username": request.user.username,
                    "email": request.user.email,
                },
                'trades': trades,
            }

            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error fetching global trades: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
