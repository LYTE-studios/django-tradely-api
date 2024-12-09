import os
import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

class BrevoEmailService:
    """Email service using BREVO (Sendinblue) API"""
    def __init__(self):
        self.api_key = settings.BREVO_API_KEY
        if not self.api_key:
            raise ImproperlyConfigured("BREVO_API_KEY is not set")
        
        self.base_url = 'https://api.brevo.com/v3/smtp/email'
        self.headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'api-key': self.api_key
        }

    def send_registration_email(self, user_email, username):
        """Send a registration confirmation email"""
        payload = {
            'sender': {
                'name': 'Trade Journal Platform',
                'email': settings.DEFAULT_FROM_EMAIL or 'noreply@tradejournalplatform.com'
            },
            'to': [{'email': user_email}],
            'subject': 'Welcome to Trade Journal Platform',
            'htmlContent': f'''
            <html>
                <body>
                    <h1>Welcome, {username}!</h1>
                    <p>Thank you for registering with Trade Journal Platform. 
                    We're excited to help you track and analyze your trades.</p>
                    <p>Get started by logging in and adding your first trade.</p>
                </body>
            </html>
            '''
        }
        return self._send_email(payload)

    def send_payment_confirmation_email(self, user_email, username, amount):
        """Send a payment confirmation email"""
        payload = {
            'sender': {
                'name': 'Trade Journal Platform',
                'email': settings.DEFAULT_FROM_EMAIL or 'noreply@tradejournalplatform.com'
            },
            'to': [{'email': user_email}],
            'subject': 'Payment Confirmation',
            'htmlContent': f'''
            <html>
                <body>
                    <h1>Payment Received</h1>
                    <p>Hi {username},</p>
                    <p>We've received your payment of ${amount}. 
                    Thank you for supporting Trade Journal Platform!</p>
                </body>
            </html>
            '''
        }
        return self._send_email(payload)

    def _send_email(self, payload):
        """Internal method to send email via BREVO API"""
        try:
            response = requests.post(
                self.base_url, 
                json=payload, 
                headers=self.headers
            )
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.RequestException as e:
            print(f"Email sending failed: {e}")
            return False, str(e)

# Create a singleton instance for easy import
brevo_email_service = BrevoEmailService()