from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import UserRegisterView, UserLoginView, CustomUserViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'users', CustomUserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('register/', UserRegisterView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # For obtaining access and refresh tokens
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # For refreshing tokens

]
