"""Regression tests for the Phase 0 security work.

These exist because the API previously had no authentication at all: the
`IsAdminOrManager` permission returned True for any request carrying
`?user_type=Admin`, and every list endpoint scoped itself from a client-supplied
`?company_id=`. Each test below pins one half of the fix — a real token, and a
company that can only come from that token.
"""

from django.test import TestCase
from rest_framework import status

from chat.models import ChatSession
from company.models import Company
from questions.models import Question
from users.models import AuthToken, User


def make_user(company, user_type, email, password="secret123"):
    user = User(
        name=f"{user_type} {email}",
        email=email,
        gender=User.Gender.OTHER,
        dob="1990-01-01",
        company=company,
        type=user_type,
    )
    user.set_password(password)
    user.save()
    return user


def bearer(token):
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def rows_of(response):
    """List endpoints are unpaginated today but may not always be."""
    body = response.json()
    return body["results"] if isinstance(body, dict) and "results" in body else body


class RegistrationTests(TestCase):
    payload = {
        "company": {
            "name": "Acme",
            "email": "acme@example.com",
            "mobile": "9990000001",
            "address": "1 A Street",
        },
        "admin": {
            "name": "Ada",
            "email": "ada@example.com",
            "password": "secret123",
            "gender": "Female",
            "dob": "1990-01-01",
        },
    }

    def test_creates_company_and_admin_and_returns_a_session(self):
        response = self.client.post(
            "/api/auth/register/", self.payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        body = response.json()
        self.assertTrue(body["token"])
        self.assertEqual(body["user"]["type"], User.Type.ADMIN)
        self.assertEqual(
            User.objects.get(email="ada@example.com").company_id,
            body["company"]["id"],
        )

    def test_raw_token_is_never_stored(self):
        response = self.client.post(
            "/api/auth/register/", self.payload, content_type="application/json"
        )
        raw = response.json()["token"]
        self.assertFalse(AuthToken.objects.filter(key_hash=raw).exists())
        self.assertEqual(AuthToken.objects.count(), 1)

    def test_registration_cannot_mint_a_non_admin(self):
        payload = {**self.payload, "admin": {**self.payload["admin"], "type": "Agent"}}
        response = self.client.post(
            "/api/auth/register/", payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["user"]["type"], User.Type.ADMIN)


class AuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(
            name="Acme", email="acme@example.com", mobile="1", address="a"
        )
        cls.admin = make_user(cls.company, User.Type.ADMIN, "admin@example.com")

    def test_query_string_role_no_longer_authorizes(self):
        """The exact bypass that used to work."""
        response = self.client.get("/api/users/?user_type=Admin")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_endpoints_are_closed_by_default(self):
        for path in ("/api/questions/", "/api/users/", "/api/unanswered-messages/"):
            with self.subTest(path=path):
                self.assertEqual(
                    self.client.get(path).status_code,
                    status.HTTP_401_UNAUTHORIZED,
                )

    def test_garbage_and_malformed_tokens_are_rejected(self):
        self.assertEqual(
            self.client.get("/api/users/", **bearer("nope")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.client.get("/api/users/", HTTP_AUTHORIZATION="Bearer").status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_login_then_logout_revokes_the_token(self):
        response = self.client.post(
            "/api/auth/login/",
            {"email": "admin@example.com", "password": "secret123"},
            content_type="application/json",
        )
        token = response.json()["token"]
        self.assertEqual(
            self.client.get("/api/questions/", **bearer(token)).status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            self.client.post("/api/auth/logout/", **bearer(token)).status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertEqual(
            self.client.get("/api/questions/", **bearer(token)).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_deactivated_user_cannot_use_an_existing_token(self):
        _, raw = AuthToken.issue(self.admin)
        User.objects.filter(pk=self.admin.pk).update(active=False)
        self.assertEqual(
            self.client.get("/api/questions/", **bearer(raw)).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class TenancyIsolationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company_a = Company.objects.create(
            name="A", email="a@example.com", mobile="1", address="a"
        )
        cls.company_b = Company.objects.create(
            name="B", email="b@example.com", mobile="2", address="b"
        )
        cls.admin_a = make_user(cls.company_a, User.Type.ADMIN, "a@admin.com")
        cls.question_a = Question.objects.create(
            company=cls.company_a, question="A?", answer="A."
        )
        cls.question_b = Question.objects.create(
            company=cls.company_b, question="B?", answer="B."
        )

    def setUp(self):
        _, self.token = AuthToken.issue(self.admin_a)
        self.auth = bearer(self.token)

    def test_list_returns_only_the_callers_company(self):
        response = self.client.get("/api/questions/", **self.auth)
        self.assertEqual(
            {row["id"] for row in rows_of(response)}, {self.question_a.id}
        )

    def test_company_id_param_cannot_widen_access(self):
        response = self.client.get(
            f"/api/questions/?company_id={self.company_b.id}", **self.auth
        )
        self.assertEqual(rows_of(response), [])

    def test_direct_id_fetch_across_tenants_is_not_found(self):
        response = self.client.get(f"/api/questions/{self.question_b.id}/", **self.auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_company_in_the_request_body_is_ignored_on_create(self):
        response = self.client.post(
            "/api/questions/",
            {"question": "Injected?", "answer": "y", "company": self.company_b.id},
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Question.objects.get(pk=response.json()["id"])
        self.assertEqual(created.company_id, self.company_a.id)

    def test_user_creation_lands_in_the_callers_company(self):
        response = self.client.post(
            "/api/managed-users/",
            {
                "name": "Mallory",
                "email": "mallory@example.com",
                "password": "secret123",
                "gender": "Other",
                "dob": "1990-01-01",
                "type": "Agent",
                "company": self.company_b.id,
            },
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            User.objects.get(email="mallory@example.com").company_id,
            self.company_a.id,
        )

    def test_vectorizing_another_company_is_denied(self):
        response = self.client.post(
            f"/api/vectorize/{self.company_b.id}/", **self.auth
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_company_endpoint_exposes_only_the_callers_own_row(self):
        self.assertEqual(
            [row["id"] for row in rows_of(self.client.get("/api/companies/", **self.auth))],
            [self.company_a.id],
        )
        self.assertEqual(
            self.client.get(f"/api/companies/{self.company_b.id}/", **self.auth).status_code,
            status.HTTP_404_NOT_FOUND,
        )


class RoleSeparationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(
            name="A", email="a@example.com", mobile="1", address="a"
        )
        cls.admin = make_user(cls.company, User.Type.ADMIN, "admin@example.com")
        cls.agent = make_user(cls.company, User.Type.AGENT, "agent@example.com")

    def test_agent_cannot_reach_manager_areas(self):
        _, raw = AuthToken.issue(self.agent)
        for path in ("/api/users/", "/api/questions/", "/api/unanswered-messages/"):
            with self.subTest(path=path):
                self.assertEqual(
                    self.client.get(path, **bearer(raw)).status_code,
                    status.HTTP_403_FORBIDDEN,
                )

    def test_agent_can_reach_their_own_inbox(self):
        _, raw = AuthToken.issue(self.agent)
        self.assertEqual(
            self.client.get("/api/agent/chats/", **bearer(raw)).status_code,
            status.HTTP_200_OK,
        )

    def test_admin_cannot_reach_the_agent_inbox(self):
        _, raw = AuthToken.issue(self.admin)
        self.assertEqual(
            self.client.get("/api/agent/chats/", **bearer(raw)).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_agent_cannot_read_another_agents_session(self):
        other = make_user(self.company, User.Type.AGENT, "other@example.com")
        session = ChatSession.objects.create(company=self.company, agent=other)
        _, raw = AuthToken.issue(self.agent)

        response = self.client.get(
            f"/api/agent/chats/history/?session_id={session.id}", **bearer(raw)
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PublicWidgetTests(TestCase):
    """The widget is unauthenticated by design, so its own guards matter more."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(
            name="Acme",
            email="acme@example.com",
            mobile="9990000001",
            address="1 A Street",
        )
        cls.session = ChatSession.objects.create(company=cls.company)

    def test_widget_config_is_open_but_exposes_only_the_name(self):
        response = self.client.get(f"/api/chat/widget/?company_id={self.company.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.json()), {"company_id", "company_name"})

    def test_every_session_gets_an_unguessable_token(self):
        other = ChatSession.objects.create(company=self.company)
        self.assertTrue(self.session.public_token)
        self.assertNotEqual(self.session.public_token, other.public_token)
        self.assertGreaterEqual(len(self.session.public_token), 24)

    def test_history_requires_the_session_token(self):
        self.assertEqual(
            self.client.get(f"/api/chat/history/?session_id={self.session.id}").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_history_with_a_wrong_token_is_indistinguishable_from_a_missing_session(self):
        wrong = self.client.get(
            f"/api/chat/history/?session_id={self.session.id}&token=wrong"
        )
        missing = self.client.get("/api/chat/history/?session_id=999999&token=wrong")
        self.assertEqual(wrong.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(wrong.json(), missing.json())

    def test_history_with_the_right_token_succeeds(self):
        response = self.client.get(
            f"/api/chat/history/?session_id={self.session.id}"
            f"&token={self.session.public_token}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.session.id)
