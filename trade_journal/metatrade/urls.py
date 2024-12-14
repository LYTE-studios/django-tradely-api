from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeleteAccount, MetaTraderAccountViewSet


urlpatterns = [
    path('login/', MetaTraderAccountViewSet.as_view({'post': 'login_account'}, ), name='metatrade_login'),
    path('delete/<int:account_id>/', DeleteAccount.as_view(), name='delete_account'),
]
