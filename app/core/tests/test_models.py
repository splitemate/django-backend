"""
Test for models
"""

from django.test import TestCase
from django.contrib.auth import get_user_model


class ModelTests(TestCase):
    """Test Models"""
    def test_create_user_with_email_successful(self):
        email = "test@example.com"
        password = "testPass@123"
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        """Test email for normalized for new users"""
        sample_email = [
            ['test1@EXAMPLE.com', 'test1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com'],
            ['test4@example.COM', 'test4@example.com']
        ]
        for email, excepted in sample_email:
            user = get_user_model().objects.create_user(email, 'sample123')
            self.assertEqual(user.email, excepted)

    def test_new_user_without_email_raise_error(self):
        """Test that creating a user without an email raise a value error"""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', 'test123')

    def test_create_superuser(self):
        """Test creating superuser"""
        user = get_user_model().objects.create_superuser(
            'test@example.com',
            'test@123'
        )
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
