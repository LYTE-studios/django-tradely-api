from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import UserRegisterView, UserLoginView

urlpatterns = [
    path('register/', UserRegisterView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # For obtaining access and refresh tokens
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # For refreshing tokens
]