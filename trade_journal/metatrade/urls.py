from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MetaTraderAccountViewSet, FetchTradesView


urlpatterns = [
    path('login/', MetaTraderAccountViewSet.as_view({'post': 'login_account'}), name='metatrade_login'),
    path('fetch-trades/', FetchTradesView.as_view({'post': 'fetch_trades'}), name='fetch_trades'),
]
