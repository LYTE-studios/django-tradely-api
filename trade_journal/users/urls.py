from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
from rest_framework.routers import DefaultRouter
from .views import (
    AccountBalanceView,
    AccountPerformanceView,
    AccountsSummaryView,
    RefreshAllAccountsView,
    UploadFileView,
    UserRegisterView,
    UserLoginView,
    TradeAccountViewSet,
    ComprehensiveTradeStatisticsView,
    TradeNoteViewSet,
    HelloThereView,
    UserGetAllTradesView,
    LeaderBoardView,
    UserProfileView,
    DeleteAccount,
    AuthenticateAccountView, ToggleUserAccountStatus,
)

# Create a router for the viewsets
router = DefaultRouter()
router.register(r'trade-accounts', TradeAccountViewSet, basename='trade-account')
router.register(r'trade-notes', TradeNoteViewSet, basename='trade-notes')

urlpatterns = [
    path('', include(router.urls)),
    # Authentication routes
    path('register/', UserRegisterView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('hello-there/', HelloThereView.as_view(), name='hello-there'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),


    # Trade account routes
    path('add-account/', AuthenticateAccountView.as_view(), name='authenticate_account'),
    path('delete/<int:account_id>/', DeleteAccount.as_view(), name='delete_account'),
    path('trade-accounts/', TradeAccountViewSet.as_view({'get': 'list', 'post': 'create'}), name='trade-account-list'),
    path('trade-accounts/<int:pk>/', TradeAccountViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='trade-account-detail'),
    path('statistics/', ComprehensiveTradeStatisticsView.as_view(), name='comprehensive-trade-statistics'),
    path('account-balance/', AccountBalanceView.as_view(), name='account-balance-statistics'),
    path('account-performance/', AccountPerformanceView.as_view(), name='trade-account-performance'),

    # Explicitly add trade notes URLs
    path('trade-notes/', TradeNoteViewSet.as_view({'get': 'list', 'post': 'create'}), name='tradenote-list'),
    path('trade-notes/<int:pk>/', TradeNoteViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='tradenote-detail'),

    path('get_all_accounts/', AccountsSummaryView.as_view(), name='get-all-trade-accounts'),
    path('get_all_trades/', UserGetAllTradesView.as_view(), name='get-all-trades'),
    path('refresh-account/', RefreshAllAccountsView.as_view(), name='refresh-account'),
    path('leaderboard/', LeaderBoardView.as_view(), name='leaderboard'),

    path('upload-file/', UploadFileView.as_view(), name='upload-file'),
    # Include the router URLs for trade accounts and manual trades
    path('', include(router.urls)),

    # Toggle user account mode
    path('toggle-account-mode/<str:account_id>/', ToggleUserAccountStatus.as_view(), name='toggle-account-mode'),
]
