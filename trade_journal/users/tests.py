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


class UserProfileTests(APITestCase):

    def setUp(self):
        self.admin_user = User.objects.create_user(username='adminuser', email='admin@example.com', password='password', is_superuser=True)
        self.regular_user = User.objects.create_user(username='testuser', email='test@example.com', password='password')
        self.client.login(username='adminuser', password='password')

    def test_admin_can_create_user_profile(self):
        url = reverse('customuser-list')
        data = {'username': 'anotheruser', 'email': 'another@example.com', 'password': 'password'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_regular_user_can_create_own_profile(self):
        self.client.logout()
        self.client.login(username='testuser', password='password')
        url = reverse('customuser-list')
        data = {'username': 'myuser', 'email': 'myuser@example.com', 'password': 'password'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_regular_user_cannot_view_all_users(self):
        self.client.logout()
        self.client.login(username='testuser', password='password')
        url = reverse('customuser-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'testuser')
        self.assertNotContains(response, 'adminuser')

    def test_regular_user_can_update_own_profile(self):
        self.client.logout()
        self.client.login(username='testuser', password='password')
        url = reverse('customuser-detail', args=[self.regular_user.id])
        data = {'username': 'updateduser'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_regular_user_cannot_update_others_profile(self):
        self.client.logout()
        self.client.login(username='testuser', password='password')
        url = reverse('customuser-detail', args=[self.admin_user.id])
        data = {'username': 'updateduser'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_user_profile(self):
        url = reverse('customuser-detail', args=[self.regular_user.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_regular_user_cannot_delete_others_profile(self):
        self.client.logout()
        self.client.login(username='testuser', password='password')
        url = reverse('customuser-detail', args=[self.admin_user.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)