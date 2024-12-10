from django.urls import path, include
from .views import FetchTradesView, TraderLockerAccountViewSet


urlpatterns = [
    path('login/', TraderLockerAccountViewSet.as_view({'post': 'login'}), name='locker_login'),
    path('fetch-trades/', FetchTradesView.as_view({'post': 'fetch_trades'}), name='fetch_trades'),
]
