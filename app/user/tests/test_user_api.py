"""
Test for user API.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status


CREATE_USER_URL = reverse("user:register")


def create_user(**params):
    """Create and return new user."""
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """Test the public features oon the user API."""

    def setUp(self) -> None:
        self.client = APIClient()

    def test_create_user_access(self):
        payload = {
            "email": "test@example.com",
            "password": "testPass@123",
            "name": "Test Name",
        }
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload["email"])
        self.assertTrue(user.check_password(payload["password"]))
        self.assertNotIn("password", res.data)

    def test_user_with_email_existing_error(self):
        """Test error returned if the user with email is exist"""
        payload = {
            "email": "test@example.com",
            "password": "testPass@123",
            "name": "Test Name",
        }
        create_user(**payload)
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    def test_password_too_short_error(self):
        """Test an error if password is less then 8 characters."""
        payload = {"email": "test@example.com", "password": "pw", "name": "Test Name"}
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exist = get_user_model().objects.filter(email=payload["email"]).exists()
        self.assertFalse(user_exist)
