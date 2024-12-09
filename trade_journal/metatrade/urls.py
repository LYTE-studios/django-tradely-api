from django.urls import path, include
from rest_framework.routers import DefaultRouter
from views import MetaTraderAccountViewSet, FetchTradesView

router = DefaultRouter()
router.register(r'metatrade', MetaTraderAccountViewSet)

urlpatterns = [
    path('login/', MetaTraderAccountViewSet.as_view(), name='metatrade_login'),
    path('fetch-trades/', FetchTradesView.as_view(), name='fetch_trades'),
]
