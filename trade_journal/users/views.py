from xmlrpc.client import Boolean

from django.utils import timezone
from django.contrib.auth import authenticate
from rest_framework import permissions, viewsets, generics
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken
from .services import TradeService, AccountService
from asgiref.sync import async_to_sync
from asgiref.sync import sync_to_async
import asyncio
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .email_service import brevo_email_service
from .models import CustomUser, TradeAccount, ManualTrade, TradeNote, UploadedFile
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    TradeAccountSerializer,
    TradeNoteSerializer,
)


import platform

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class HelloThereView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"message": "Hello There!"})


class AuthenticateAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        server_name = request.data.get("server_name")
        account_name = request.data.get("account_name")
        username = request.data.get("username")
        password = request.data.get("password")
        platform = request.data.get("platform")

        if not all([server_name, username, password, platform]):
            return Response(
                {
                    "error": "All fields are required: server_name, username, password, and platform."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            AccountService.authenticate(
                username, password, server_name, platform, account_name, request.user
            )
            return Response(
                {"message": "Account authenticated."}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeleteAccount(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        account_id = kwargs["account_id"]

        if not account_id:
            return Response(
                {"error": "All fields are required: account_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            account = TradeAccount.objects.get(id=account_id)
        except TradeAccount.DoesNotExist:
            return Response(
                {"error": "Account not found."}, status=status.HTTP_404_NOT_FOUND
            )

        AccountService.delete_account(account)

        return Response({"message": "Account deleted."}, status=status.HTTP_200_OK)


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
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        user = authenticate(username=username, password=password)
        if user is not None:
            token = AccessToken.for_user(user)
            return Response({"access": str(token)})
        return Response({"detail": "Invalid credentials"}, status=401)


class UserProfileView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        return Response(
            {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        )

    def put(self, request, *args, **kwargs):
        user = request.user

        try:
            user.first_name = request.data.get("first_name")
        except:
            pass
        try:
            user.last_name = request.data.get("last_name")
        except:
            pass

        user.save()

        return Response(
            {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        )


class BaseModelViewSet(viewsets.ModelViewSet):
    """
    Enhanced base ViewSet with consistent response formatting
    """

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance = self.perform_create(serializer)

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return Response(
                {"success": False, "errors": e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop("partial", False)
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return Response({"success": True, "data": serializer.data})
        except ValidationError as e:
            return Response(
                {"success": False, "errors": e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(
                {"success": True, "message": "Object successfully deleted"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"success": False, "errors": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class TradeAccountViewSet(BaseModelViewSet):
    serializer_class = TradeAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TradeAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)


class TradeNoteViewSet(viewsets.ModelViewSet):
    queryset = TradeNote.objects.all()
    serializer_class = TradeNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Base queryset filtered by user
        queryset = TradeNote.objects.filter(user=self.request.user)

        # Check if date parameter is provided in the request
        date_param = self.request.query_params.get("date", None)
        if date_param:
            try:
                # Convert the date string to a date object
                date = timezone.datetime.strptime(date_param, "%Y-%m-%d").date()
                # Filter queryset by the specific date
                queryset = queryset.filter(note_date=date)
            except ValueError:
                # Handle invalid date format
                return TradeNote.objects.none()

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)


class UserRegistrationView(APIView):
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Send registration email
            try:
                success, _ = brevo_email_service.send_registration_email(
                    user_email=user.email, username=user.username
                )
                if not success:
                    # Log email sending failure but don't block registration
                    print(f"Failed to send registration email to {user.email}")
            except Exception as e:
                print(f"Email service error: {e}")

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AccountsSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            disabled = request.query_params.get("disabled", None)
            accounts = TradeService.get_all_accounts(request.user, disabled=disabled)
            return Response(
                {"accounts": [account.to_dict() for account in accounts]},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": f"Error fetching accounts: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AccountPerformanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            disabled = request.query_params.get("disabled", None)
            performance = TradeService.get_account_performance(
                request.user, disabled=disabled
            )
            return Response(performance, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Error fetching account performance: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ComprehensiveTradeStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from_date = request.query_params.get("from")
        until_date = request.query_params.get("to")
        disabled = request.query_params.get("disabled", None)

        parsed_from_date = None
        parsed_until_date = None

        if from_date and until_date:
            parsed_from_date = timezone.datetime.strptime(from_date, "%Y-%m-%d")
            parsed_until_date = timezone.datetime.strptime(until_date, "%Y-%m-%d")

        # Fetch trades using the service method with optional datetime filtering
        trades = TradeService.get_all_trades(
            request.user, from_date=parsed_from_date, to_date=parsed_until_date
        )

        accounts = TradeService.get_all_accounts(request.user, disabled=disabled)

        statistics = TradeService.calculate_statistics(trades, accounts)

        return Response(statistics)


class AccountBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the from and to dates from the request query parameters
        from_date = request.query_params.get("from")
        until_date = request.query_params.get("to")

        # Parse datetime parameters
        parsed_from_date = None
        parsed_until_date = None

        if from_date and until_date:
            parsed_from_date = timezone.datetime.strptime(from_date, "%Y-%m-%d")
            parsed_until_date = timezone.datetime.strptime(until_date, "%Y-%m-%d")

        # Fetch trades using the service method with optional datetime filtering
        balance_chart = TradeService.get_account_balance_chart(
            request.user, from_date=parsed_from_date, to_date=parsed_until_date
        )

        return Response(balance_chart)


class LeaderBoardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        leaderboard = TradeService.get_leaderboard()
        return Response(leaderboard)


class RefreshAllAccountsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(csrf_exempt)
    def post(self, request, *args, **kwargs):
        force_refresh = request.data.get("force_refresh", False)

        # Directly call the asynchronous function using async_to_sync
        async_to_sync(AccountService.check_refresh)(
            request.user, force_refresh=force_refresh
        )

        return Response({"message": "Refresh complete"}, status=status.HTTP_200_OK)


class UserGetAllTradesView(APIView):
    def get(self, request):

        try:

            from_date = request.query_params.get("from")
            until_date = request.query_params.get("to")

            # Parse datetime parameters
            parsed_from_date = None
            parsed_until_date = None

            if from_date:
                parsed_from_date = timezone.datetime.strptime(from_date, "%Y-%m-%d")

            if until_date:
                parsed_until_date = timezone.datetime.strptime(until_date, "%Y-%m-%d")

            # Fetch trades using the service method with optional datetime filtering
            trades = TradeService.get_all_trades(
                request.user, from_date=parsed_from_date, to_date=parsed_until_date
            )

            response_data = {
                "user": {
                    "id": request.user.id,
                    "username": request.user.username,
                    "email": request.user.email,
                },
                "trades": [trade.to_dict() for trade in trades],
            }

            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error fetching global trades: {str(e)}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UploadFileView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            file = request.FILES["file"]
            uploaded_file = UploadedFile.objects.create(user=request.user, file=file)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({"url": uploaded_file.file.url}, status=status.HTTP_201_CREATED)


class ToggleUserAccountStatus(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, account_id=None):
        try:
            if account_id is None:
                return Response(
                    {"error": "account ID is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Retrieve the boolean parameter 'mode'
            disable = request.data.get("disable", False)

            # Ensure the mode is a boolean
            if not isinstance(disable, bool):
                return Response(
                    {"error": "mode must be a boolean (true or false)"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = request.user
            trade_account = TradeAccount.objects.get(id=account_id, user=user)

            trade_account.disabled = disable
            response = "account enabled" if not disable else "account disabled"
            trade_account.save()

            return Response({"response": response}, status=status.HTTP_200_OK)

        except TradeAccount.DoesNotExist:
            return Response(
                {"error": "trade account not found"}, status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
