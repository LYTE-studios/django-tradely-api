from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import UserRegisterView, UserLoginView, CustomUserViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'users', CustomUserViewSet)
from rest_framework.routers import DefaultRouter
from .views import (
    UserRegisterView,
    UserLoginView,
    TradeAccountViewSet,
    ManualTradeViewSet,
    ComprehensiveTradeStatisticsView,
    TradeAccountPerformanceView,
    TradeNoteViewSet
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
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # For obtaining access and refresh tokens
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # For refreshing tokens

    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
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

    # Include the router URLs for trade accounts and manual trades
    path('', include(router.urls)),
]