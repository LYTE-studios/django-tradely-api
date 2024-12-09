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
from .email_service import BrevoEmailService
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField, Avg
from django.db.models.functions import Coalesce
from django.db.models import Max, Min
from decimal import Decimal
from .email_service import brevo_email_service


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

def some_view(request):
    email_service = BrevoEmailService()
    email_service.send_registration_confirmation(
        user_email='user@example.com', 
        username='JohnDoe'
    )

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal
from django.utils import timezone

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
    