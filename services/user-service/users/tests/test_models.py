"""
Tests for user models
"""
import pytest
from django.contrib.auth import get_user_model
from users.models import UserPreference

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestUserModel:
    """Test User model"""
    
    def test_create_user(self):
        """Test creating a regular user"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            name='Test User'
        )
        
        assert user.email == 'test@example.com'
        assert user.name == 'Test User'
        assert user.check_password('testpass123')
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.preferences is not None
    
    def test_create_superuser(self):
        """Test creating a superuser"""
        user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            name='Admin User'
        )
        
        assert user.is_active is True
        assert user.is_staff is True
        assert user.is_superuser is True
    
    def test_user_str_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            name='Test User'
        )
        
        assert str(user) == 'test@example.com'
    
    def test_user_preferences_created_automatically(self):
        """Test that preferences are created automatically"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            name='Test User'
        )
        
        assert user.preferences is not None
        assert isinstance(user.preferences, UserPreference)
        assert user.preferences.email is True
        assert user.preferences.push is True


class TestUserPreferenceModel:
    """Test UserPreference model"""
    
    def test_create_preference(self):
        """Test creating user preferences"""
        preference = UserPreference.objects.create(
            email=True,
            push=False
        )
        
        assert preference.email is True
        assert preference.push is False
    
    def test_preference_str_representation(self):
        """Test preference string representation"""
        preference = UserPreference.objects.create(
            email=True,
            push=False
        )
        
        assert str(preference) == "Preferences(email=True, push=False)"
