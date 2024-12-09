from rest_framework import generics, viewsets, permissions
from rest_framework_simplejwt.tokens import AccessToken
from .serializers import UserRegistrationSerializer, UserLoginSerializer
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny
from .models import CustomUser
from .serializers import CustomUserSerializer
from rest_framework.exceptions import PermissionDenied


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


class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Check if the user is an admin
        if self.request.user.is_superuser or self.request.user.is_staff:
            return CustomUser.objects.all()
        # Regular users can only access their own profile
        return CustomUser.objects.filter(pk=self.request.user.pk)

    def perform_create(self, serializer):
        serializer.save()

    def update(self, request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.is_staff:
            if request.user.pk != kwargs['pk']:
                raise PermissionDenied("You do not have permission to update this user.")
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.is_staff:
            if request.user.pk != kwargs['pk']:
                raise PermissionDenied("You do not have permission to delete this user.")
        return super().destroy(request, *args, **kwargs)
