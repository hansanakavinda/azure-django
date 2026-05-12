# tests/test_authentication/test_views.py

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient


class TestRegister(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_valid_registration(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'alice',
            'password': 'Secure@Pass99',
            'confirm_password': 'Secure@Pass99',
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['success'])

    def test_weak_password_rejected(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'alice',
            'password': 'password',
            'confirm_password': 'password',
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])

    def test_duplicate_username_rejected(self):
        User.objects.create_user(username='alice', password='Test@1234')

        response = self.client.post('/api/auth/register/', {
            'username': 'alice',
            'password': 'Secure@Pass99',
            'confirm_password': 'Secure@Pass99',
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])


class TestLogin(TestCase):

    def setUp(self):
        self.client = APIClient()
        User.objects.create_user(username='alice', password='Secure@Pass99')

    def test_valid_login(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'alice',
            'password': 'Secure@Pass99',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])

    def test_wrong_password(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'alice',
            'password': 'WrongPass@123',
        })
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data['success'])

class TestLogout(TestCase):

    def setUp(self):
        self.client = APIClient()
        User.objects.create_user(username='alice', password='Secure@Pass99')

        response = self.client.post('/api/auth/login/', {
            'username': 'alice',
            'password': 'Secure@Pass99',
        })

        # Correct path to tokens
        self.access = response.data['data']['access']
        self.refresh = response.data['data']['refresh']

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.access}"
        )

    def test_valid_logout(self):
        response = self.client.post('/api/auth/logout/', {
            'refresh': self.refresh,
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])

    def test_token_unusable_after_logout(self):
        self.client.post('/api/auth/logout/', {
            'refresh': self.refresh,
        })

        self.client.credentials()
        response = self.client.post('/api/auth/token/refresh/', {
            'refresh': self.refresh,
        })
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.data['success'])