"""Tests for authentication, roles and tenant isolation."""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.enums import UserRole

User = get_user_model()


class UserModelTests(APITestCase):
    def test_create_user_defaults_to_agent(self):
        user = User.objects.create_user(email="a@x.com", password="pass12345", full_name="A")
        self.assertEqual(user.role, UserRole.AGENT)
        self.assertTrue(user.check_password("pass12345"))
        self.assertFalse(user.is_staff)

    def test_create_superuser(self):
        admin = User.objects.create_superuser(email="root@x.com", password="pass12345")
        self.assertTrue(admin.is_super_admin)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_email_is_required(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="x")


class AuthFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="login@x.com", password="pass12345", full_name="Log In"
        )

    def test_login_returns_tokens_and_user(self):
        resp = self.client.post(
            reverse("login"), {"email": "login@x.com", "password": "pass12345"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["user"]["email"], "login@x.com")

    def test_login_with_bad_password_fails(self):
        resp = self.client.post(
            reverse("login"), {"email": "login@x.com", "password": "wrong"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_auth(self):
        resp = self.client.get("/api/v1/accounts/users/me/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_profile_when_authenticated(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get("/api/v1/accounts/users/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["user"]["email"], "login@x.com")
