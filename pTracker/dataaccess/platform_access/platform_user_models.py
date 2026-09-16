from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
""" The following tables are created here
PlatformUser

Note: PlatformUser is a standalone identity for SaaS platform operators.
It is intentionally NOT registered as AUTH_USER_MODEL, so it never
interacts with the existing employee auth_user table or login flow.
"""

class PlatformUserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Platform user requires an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)


class PlatformUser(AbstractBaseUser):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=250, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = PlatformUserManager()

    class Meta:
        db_table = 'platform_user'

    def __str__(self):
        return self.email
