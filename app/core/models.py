"""
Database Models
"""
from typing import Any
from django.db import models
import string
import secrets
from django.contrib.auth import get_user_model

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)


class ActiveManager(models.Manager):
    def get_queryset(self):
        """Return only active records (soft delete enabled)"""
        return super().get_queryset().filter(is_active=True)


class UserSources(models.TextChoices):
    STANDARD = 'standard', 'Standard'
    GOOGLE = 'google', 'Google'


def generate_unique_random_string(length=10):
    characters = string.ascii_letters + string.digits
    User = get_user_model()
    while True:
        random_string = ''.join(secrets.choice(characters) for _ in range(length))
        if not User.objects.filter(invite_token=random_string).exists():
            return random_string


class UserManager(BaseUserManager):
    """Managger for users"""

    def create_user(self, email, password=None, **extra_fields: Any):
        """Create a new user"""
        if not email:
            raise ValueError("User must have an email address")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields: Any):
        """Creatte a new super user"""
        user = self.create_user(email, password, **extra_fields)
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    """User in the system"""

    email = models.EmailField(
        max_length=255, unique=True, verbose_name="Email", help_text="Email"
    )
    name = models.CharField(
        max_length=255, verbose_name="Name", help_text="Name of the user"
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(
        default=False, verbose_name="Is Internal user?", help_text="Is Internal User?"
    )
    friends = models.ManyToManyField('self', symmetrical=True, blank=True, help_text="Fiend list of user")
    invite_token = models.CharField(max_length=10, null=True, unique=True, help_text="Token to add friend with other users")
    user_source = models.CharField(
        max_length=10, choices=UserSources.choices, default='standard',
        verbose_name="User Source", help_text="Indicates the source of the user registration (e.g., 'google')."
    )
    is_email_verified = models.BooleanField(
        default=False, verbose_name="Email Verified",
        help_text="Indicates whether the user has verified their email."
    )
    image_url = models.URLField(max_length=500, blank=True, null=False, default="")

    objects = UserManager()

    USERNAME_FIELD = "email"

    class Meta:
        indexes = [
            models.Index(fields=['invite_token']),
        ]

    def save(self, *args, **kwargs):
        if not self.invite_token:
            self.invite_token = generate_unique_random_string()
        super().save(*args, **kwargs)

    def get_users_details(self, list_of_users_ids):
        """Get user details"""
        users = [
            {**user, 'id': str(user['id'])}
            for user in User.objects.filter(id__in=list_of_users_ids).values('id', 'name', 'email', 'image_url')
        ]
        return users
