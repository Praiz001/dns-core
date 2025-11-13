"""Test configuration and imports"""
import pytest
from app.config import settings
from app.providers.fcm import FCMProvider
from app.services.push_service import PushService


def test_settings_loaded():
    """Test that settings are loaded correctly"""
    assert settings.SERVICE_NAME == "push-service"
    assert settings.SERVICE_VERSION == "1.0.0"
    assert settings.RABBITMQ_QUEUE == "push.queue"


def test_fcm_provider_initialization():
    """Test FCM provider can be initialized"""
    provider = FCMProvider()
    assert provider.get_provider_name() == "fcm"
    assert provider.api_url == "https://fcm.googleapis.com/fcm/send"


def test_push_service_initialization():
    """Test Push service can be initialized"""
    provider = FCMProvider()
    service = PushService(provider)
    assert service.push_provider is not None
    assert service.user_service_url == settings.USER_SERVICE_URL
    assert service.template_service_url == settings.TEMPLATE_SERVICE_URL
