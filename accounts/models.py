import random

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username must be set")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("user_type", "Admin")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        return self.create_user(username, email, password, **extra_fields)


class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ("Admin", "Admin"),
        ("User", "User"),
    )
    email = models.EmailField(unique=True)  # ✅ make email unique
    user_type = models.CharField(
        max_length=10, choices=USER_TYPE_CHOICES, default="User"
    )
    is_email_verified = models.BooleanField(default=False)
    email_otp = models.CharField(max_length=6, blank=True, null=True)
    last_otp_sent = models.DateTimeField(blank=True, null=True)

    def generate_otp(self):
        self.email_otp = str(random.randint(100000, 999999))
        self.last_otp_sent = timezone.now()
        self.save()

    def __str__(self):
        return self.username
