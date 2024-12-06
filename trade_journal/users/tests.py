from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class UserTests(APITestCase):
    def test_user_registration(self):
        url = reverse('register')
        data = {'username': 'testuser', 'email': 'test@example.com', 'password': 'testpass123'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_user_login(self):
        url = reverse('register')
        self.client.post(url, {'username': 'testuser', 'email': 'test@example.com', 'password': 'testpass123'},
                         format='json')
        login_url = reverse('login')
        response = self.client.post(login_url, {'username': 'testuser', 'password': 'testpass123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_token_obtain(self):
        url = reverse('register')
        self.client.post(url, {'username': 'testuser', 'email': 'test@example.com', 'password': 'testpass123'},
                         format='json')
        token_url = reverse('token_obtain_pair')
        response = self.client.post(token_url, {'username': 'testuser', 'password': 'testpass123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_token_refresh(self):
        url = reverse('register')
        self.client.post(url, {'username': 'testuser', 'email': 'test@example.com', 'password': 'testpass123'},
                         format='json')
        token_url = reverse('token_obtain_pair')
        response = self.client.post(token_url, {'username': 'testuser', 'password': 'testpass123'}, format='json')
        refresh_token = response.data['refresh']

        refresh_url = reverse('token_refresh')
        refresh_response = self.client.post(refresh_url, {'refresh': refresh_token}, format='json')
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.data)