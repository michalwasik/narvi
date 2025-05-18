from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
import random
import string
from datetime import timedelta
from django.utils import timezone
import uuid

class CustomUserManager(BaseUserManager):
    """
    Custom user manager for our CustomUser model with required email field.
    """
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError(_('The Username must be set'))
        if not email:
            raise ValueError(_('The Email must be set'))
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(username, email, password, **extra_fields)

class CustomUser(AbstractUser):
    """
    Custom User model with two-factor authentication support.
    """
    class TwoFactorMethod(models.TextChoices):
        NONE = 'NONE', _('None')
        SMS = 'SMS', _('SMS')
        GOOGLE_AUTH = 'GOOGLE_AUTH', _('Google Authenticator')
    
    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField(_('phone number'), max_length=15, blank=True, null=True)
    two_fa_method = models.CharField(
        _('two-factor authentication method'),
        max_length=15,
        choices=TwoFactorMethod.choices,
        default=TwoFactorMethod.NONE
    )
    two_fa_secret = models.CharField(_('two-factor secret key'), max_length=50, blank=True, null=True)
    
    objects = CustomUserManager()
    
    def __str__(self):
        return self.username

class TwoFactorCode(models.Model):
    """
    Model to store temporary verification codes for two-factor authentication.
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='two_factor_codes')
    code = models.CharField(_('verification code'), max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username} - {self.code}"
    
    @classmethod
    def generate_code(cls, user, expiry_minutes=10):
        """
        Generate a new verification code for a user.
        """
        # Generate a random 6-digit code
        code = ''.join(random.choices(string.digits, k=6))
        
        # Calculate expiry time
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
        
        # Create and return the code
        return cls.objects.create(
            user=user,
            code=code,
            expires_at=expires_at
        )
    
    @property
    def is_valid(self):
        """
        Check if the code is still valid (not expired and not used).
        """
        return not self.is_used and self.expires_at > timezone.now()

class TemporaryToken(models.Model):
    """
    Temporary token issued after first step of authentication.
    Used to track user between step 1 and step 2 of 2FA.
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='temp_tokens')
    token = models.CharField(_('temporary token'), max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username} - {self.token[:10]}..."
    
    @classmethod
    def generate_token(cls, user, expiry_minutes=15):
        """
        Generate a temporary token for a user.
        """
        # Generate a unique token
        token = str(uuid.uuid4())
        
        # Calculate expiry time
        expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
        
        # Create and return the token
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )
    
    @property
    def is_valid(self):
        """
        Check if the token is still valid (not expired and not used).
        """
        return not self.is_used and self.expires_at > timezone.now()
