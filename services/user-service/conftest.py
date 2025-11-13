"""
Pytest configuration and fixtures
"""

# isort: skip_file
# Imports must be in specific order for Django setup

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Override any external DJANGO_SETTINGS_MODULE
os.environ["DJANGO_SETTINGS_MODULE"] = "user_service.settings"

# Import Django and setup
import django  # noqa: E402

django.setup()

# Import Django and testing modules after setup
import pytest  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

User = get_user_model()


@pytest.fixture
def api_client():
    """Return an API client for testing"""
    return APIClient()


@pytest.fixture
def user_data():
    """Sample user data for testing"""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "password": "TestPass123!",
        "preferences": {"email": True, "push": True},
    }


@pytest.fixture
def create_user(db, user_data):
    """Factory fixture to create a user"""

    def _create_user(**kwargs):
        data = user_data.copy()
        data.update(kwargs)
        preferences = data.pop("preferences", None)

        user = User.objects.create_user(**data)

        if preferences and user.preferences:
            for key, value in preferences.items():
                setattr(user.preferences, key, value)
            user.preferences.save()

        return user

    return _create_user


@pytest.fixture
def authenticated_client(api_client, create_user):
    """Return an authenticated API client"""
    user = create_user()
    api_client.force_authenticate(user=user)
    return api_client, user
