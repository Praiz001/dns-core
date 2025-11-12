"""
Integration tests for user API endpoints
"""

import pytest
from django.urls import reverse
from rest_framework import status

pytestmark = pytest.mark.django_db


class TestUserRegistration:
    """Test user registration endpoint"""

    def test_register_user_success(self, api_client, user_data):
        """Test successful user registration"""
        url = reverse("users:user-register")
        response = api_client.post(url, user_data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert "data" in response.data
        assert "user" in response.data["data"]
        assert "access_token" in response.data["data"]
        assert response.data["data"]["user"]["email"] == user_data["email"]

    def test_register_user_duplicate_email(self, api_client, create_user, user_data):
        """Test registration with duplicate email"""
        create_user(email=user_data["email"])

        url = reverse("users:user-register")
        response = api_client.post(url, user_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False

    def test_register_user_invalid_email(self, api_client, user_data):
        """Test registration with invalid email"""
        user_data["email"] = "invalid-email"

        url = reverse("users:user-register")
        response = api_client.post(url, user_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False

    def test_register_user_weak_password(self, api_client, user_data):
        """Test registration with weak password"""
        user_data["password"] = "123"

        url = reverse("users:user-register")
        response = api_client.post(url, user_data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False


class TestUserLogin:
    """Test user login endpoint"""

    def test_login_success(self, api_client, create_user):
        """Test successful login"""
        create_user(email="test@example.com", password="TestPass123!")

        url = reverse("users:auth-login")
        response = api_client.post(url, {"email": "test@example.com", "password": "TestPass123!"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "access_token" in response.data["data"]

    def test_login_invalid_credentials(self, api_client, create_user):
        """Test login with invalid credentials"""
        create_user(email="test@example.com", password="TestPass123!")

        url = reverse("users:auth-login")
        response = api_client.post(url, {"email": "test@example.com", "password": "WrongPassword"}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["success"] is False

    def test_login_nonexistent_user(self, api_client):
        """Test login with non-existent user"""
        url = reverse("users:auth-login")
        response = api_client.post(url, {"email": "nonexistent@example.com", "password": "TestPass123!"}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["success"] is False


class TestUserProfile:
    """Test user profile endpoints"""

    def test_get_profile_authenticated(self, authenticated_client):
        """Test getting user profile when authenticated"""
        client, user = authenticated_client

        url = reverse("users:user-profile")
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["email"] == user.email

    def test_get_profile_unauthenticated(self, api_client):
        """Test getting profile when not authenticated"""
        url = reverse("users:user-profile")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_profile(self, authenticated_client):
        """Test updating user profile"""
        client, user = authenticated_client

        url = reverse("users:user-profile")
        response = client.patch(url, {"name": "Updated Name", "push_token": "new_token_123"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["name"] == "Updated Name"
        assert response.data["data"]["push_token"] == "new_token_123"

    def test_delete_profile(self, authenticated_client):
        """Test deleting user profile (soft delete)"""
        client, user = authenticated_client

        url = reverse("users:user-profile")
        response = client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

        # Verify user is deactivated
        user.refresh_from_db()
        assert user.is_active is False


class TestUserPreferences:
    """Test user preferences endpoints"""

    def test_get_preferences(self, authenticated_client):
        """Test getting user preferences"""
        client, user = authenticated_client

        url = reverse("users:user-preferences")
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "email" in response.data["data"]
        assert "push" in response.data["data"]

    def test_update_preferences(self, authenticated_client):
        """Test updating user preferences"""
        client, user = authenticated_client

        url = reverse("users:user-preferences")
        response = client.patch(url, {"email": False, "push": False}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["email"] is False
        assert response.data["data"]["push"] is False


class TestHealthCheck:
    """Test health check endpoint"""

    def test_health_check(self, api_client):
        """Test health check returns healthy status"""
        url = reverse("users:health-check")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["data"]["status"] == "healthy"
