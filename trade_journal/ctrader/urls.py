from django.urls import path, include
from .views import CTraderAccountViewSet, DeleteAccount


urlpatterns = [
    path(
        "login/",
        CTraderAccountViewSet.as_view({"post": "login"}),
        name="c_trader_login",
    ),
    path(
        "delete-account/<int:account_id>/",
        DeleteAccount.as_view(),
        name="c_trader_delete-account",
    ),
]
