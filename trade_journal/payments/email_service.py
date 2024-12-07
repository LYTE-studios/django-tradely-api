# email_service.py

from importlib import import_module
from .email_backends import EMAIL_BACKEND_MAPPING


def get_dynamic_email_backend(service_name, credentials):
    if service_name not in EMAIL_BACKEND_MAPPING:
        raise ValueError(f"Unsupported email service: {service_name}")

    # Import backend dynamically
    backend_path = EMAIL_BACKEND_MAPPING[service_name]
    backend_class = import_module(backend_path)

    match service_name:
        case 'Mailjet':
            return backend_class.EmailBackend(api_key=credentials.get('api_key'), secret_key=credentials.get('api_secret'))
        case 'MailerSend':
            return backend_class.EmailBackend(api_token=credentials.get('api_key'))
        case 'Postmark':
            return backend_class.EmailBackend(server_token=credentials.get('api_key'))
        case _:
            return backend_class.EmailBackend(api_key=credentials.get('api_key'))
