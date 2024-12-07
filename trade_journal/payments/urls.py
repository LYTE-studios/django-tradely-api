from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet

router = DefaultRouter()
router.register(r'payments', PaymentViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('webhook/', PaymentViewSet.as_view({'post': 'stripe_webhook'}), name='stripe-webhook'),
]