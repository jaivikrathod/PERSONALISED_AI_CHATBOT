"""Tests for company onboarding and tenant isolation."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from core.enums import CompanyStatus, UserRole

from .models import Company, UserCompany

User = get_user_model()


class CompanyOnboardTests(APITestCase):
    def test_onboard_creates_company_and_admin(self):
        payload = {
            "company": {"name": "Acme", "email": "ops@acme.com"},
            "admin": {
                "email": "admin@acme.com",
                "full_name": "Acme Admin",
                "password": "StrongPass123",
                "password_confirm": "StrongPass123",
            },
        }
        resp = self.client.post("/api/v1/companies/companies/onboard/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        admin = User.objects.get(email="admin@acme.com")
        self.assertEqual(admin.role, UserRole.COMPANY_ADMIN)
        self.assertIsNotNone(admin.company_id)
        # Signal should have created the membership row.
        self.assertTrue(UserCompany.objects.filter(user=admin, company=admin.company).exists())


class TenantIsolationTests(APITestCase):
    def setUp(self):
        self.company_a = Company.objects.create(name="A", email="a@a.com", status=CompanyStatus.ACTIVE)
        self.company_b = Company.objects.create(name="B", email="b@b.com", status=CompanyStatus.ACTIVE)
        self.admin_a = User.objects.create_user(
            email="a@x.com", password="pass12345", role=UserRole.COMPANY_ADMIN, company=self.company_a
        )

    def test_user_only_sees_own_company(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.get("/api/v1/companies/companies/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        names = [c["name"] for c in resp.data["results"]]
        self.assertIn("A", names)
        self.assertNotIn("B", names)

    def test_user_cannot_fetch_other_company(self):
        self.client.force_authenticate(self.admin_a)
        resp = self.client.get(f"/api/v1/companies/companies/{self.company_b.uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
