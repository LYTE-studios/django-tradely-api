# middleware.py
from django.utils.deprecation import MiddlewareMixin


class EmailServiceMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.email_service_name = request.headers.get("X-Email-Service")
        request.email_service_api_key = request.headers.get("X-Email-Service-API-Key")
        request.email_service_api_secret = request.headers.get(
            "X-Email-Service-API-Secret"
        )
