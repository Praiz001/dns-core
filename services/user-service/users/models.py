"""
User models
"""
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user"""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class UserPreference(models.Model):
    """User notification preferences"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.BooleanField(default=True, help_text="Enable email notifications")
    push = models.BooleanField(default=True, help_text="Enable push notifications")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_preferences'
        verbose_name = 'User Preference'
        verbose_name_plural = 'User Preferences'
    
    def __str__(self):
        return f"Preferences(email={self.email}, push={self.push})"


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=255)
    push_token = models.CharField(max_length=512, blank=True, null=True, help_text="FCM/APNS device token")
    preferences = models.OneToOneField(
        UserPreference,
        on_delete=models.CASCADE,
        related_name='user',
        null=True,
        blank=True
    )
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        """Override save to create preferences if not exists"""
        if not self.preferences:
            self.preferences = UserPreference.objects.create()
        super().save(*args, **kwargs)


class IdempotencyKey(models.Model):
    """Store idempotency keys to prevent duplicate processing"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_id = models.CharField(max_length=255, unique=True, db_index=True)
    endpoint = models.CharField(max_length=255)
    response_data = models.JSONField(null=True, blank=True)
    status_code = models.IntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'idempotency_keys'
        verbose_name = 'Idempotency Key'
        verbose_name_plural = 'Idempotency Keys'
        indexes = [
            models.Index(fields=['request_id']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.request_id} - {self.endpoint}"
    
    def is_expired(self):
        """Check if the idempotency key has expired"""
        return timezone.now() > self.expires_at
