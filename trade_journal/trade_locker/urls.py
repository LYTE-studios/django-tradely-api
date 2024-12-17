from django.urls import path, include
from .views import TraderLockerAccountViewSet, DeleteAccount


urlpatterns = [
    path('login/', TraderLockerAccountViewSet.as_view({'post': 'login'}), name='locker_login'),
    path('delete-account/<int:account_id>/', DeleteAccount.as_view(), name='delete-account'),
]
