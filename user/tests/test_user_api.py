from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


CREATE_USER_URL = reverse("user:create")
TOKEN_URL = reverse("user:token_obtain_pair")
ME_URL = reverse("user:me")


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(APITestCase):
    """Tests for unauthenticated user requests"""

    def test_create_user_success(self):
        payload = {
            "email": "test@example.com",
            "password": "testpass123",
        }

        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        user = get_user_model().objects.get(email=payload["email"])
        self.assertTrue(user.check_password(payload["password"]))

        self.assertNotIn("password", res.data)

    def test_create_user_duplicate_email(self):
        payload = {
            "email": "test@example.com",
            "password": "testpass123",
        }

        create_user(**payload)
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_user_password_too_short(self):
        payload = {
            "email": "test@example.com",
            "password": "123",
        }

        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_success(self):
        payload = {
            "email": "test@example.com",
            "password": "testpass123",
        }

        create_user(**payload)
        res = self.client.post(TOKEN_URL, payload)

        self.assertIn("access", res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_invalid_credentials(self):
        create_user(email="test@example.com", password="goodpass")

        payload = {
            "email": "test@example.com",
            "password": "wrongpass",
        }

        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn("access", res.data)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized_user_cannot_access_me(self):
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(APITestCase):
    """Tests for authenticated user"""

    def setUp(self):
        self.user = create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], self.user.email)

    def test_post_not_allowed_on_me(self):
        res = self.client.post(ME_URL, {})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        payload = {
            "email": "new@example.com",
            "password": "newpass123",
        }

        res = self.client.put(ME_URL, payload)

        self.user.refresh_from_db()

        self.assertEqual(self.user.email, payload["email"])
        self.assertTrue(self.user.check_password(payload["password"]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
