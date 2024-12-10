from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
from rest_framework.routers import DefaultRouter
from .views import (
    UserRegisterView,
    UserLoginView,
    TradeAccountViewSet,
    ManualTradeViewSet,
    ComprehensiveTradeStatisticsView,
    TradeAccountPerformanceView,
    TradeNoteViewSet,
    HelloThereView,
    UserGetAllTradeAccountsView
)

# Create a router for the viewsets
router = DefaultRouter()
router.register(r'trade-accounts', TradeAccountViewSet, basename='trade-account')
router.register(r'manual-trades', ManualTradeViewSet, basename='manual-trade')
router.register(r'trade-notes', TradeNoteViewSet, basename='trade-notes')

urlpatterns = [
    path('', include(router.urls)),
    # Authentication routes
    path('register/', UserRegisterView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('hello-there', HelloThereView.as_view(), name='hello-there'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Trade account routes
    path('api/trade-accounts/', TradeAccountViewSet.as_view({'get': 'list', 'post': 'create'}), name='trade-account-list'),
    path('api/trade-accounts/<int:pk>/', TradeAccountViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='trade-account-detail'),
    path('api/manual-trades/', ManualTradeViewSet.as_view({'get': 'list', 'post': 'create'}), name='manual-trade-list'),
    path('api/manual-trades/<int:pk>/', ManualTradeViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }),),
    path('api/statistics/', ComprehensiveTradeStatisticsView.as_view(), name='comprehensive-trade-statistics'),
    path('api/account-performance/', TradeAccountPerformanceView.as_view(), name='trade-account-performance'),

    # Explicitly add trade notes URLs
    path('trade-notes/', TradeNoteViewSet.as_view({'get': 'list', 'post': 'create'}), name='tradenote-list'),
    path('trade-notes/<int:pk>/', TradeNoteViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='tradenote-detail'),

    path('get_all_trades/', UserGetAllTradeAccountsView.as_view(), name='get-all-trade-accounts'),

    # Include the router URLs for trade accounts and manual trades
    path('', include(router.urls)),
]
