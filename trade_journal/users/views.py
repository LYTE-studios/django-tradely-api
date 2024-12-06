from rest_framework import generics, permissions
from rest_framework_simplejwt.tokens import AccessToken
from .serializers import UserRegistrationSerializer, UserLoginSerializer
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny
from .models import CustomUser


class UserRegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()  # or your own user model
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]  # Allow public access


class UserLoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            token = AccessToken.for_user(user)
            return Response({'access': str(token)})
        return Response({'detail': 'Invalid credentials'}, status=401)
