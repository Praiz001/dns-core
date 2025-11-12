"""
Unit tests for Email Service.

Tests cover:
- Complete email processing workflow
- User preference handling
- Template rendering integration
- Email sending with retries
- Circuit breaker behavior
- Webhook handling
- Error scenarios
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4, UUID
from datetime import datetime

from app.services.email_service import EmailService
from app.schemas.email import QueueMessage, UserPreferences, TemplateRenderResponse
from app.models.email_delivery import EmailDelivery
from app.providers.base import SendResult


@pytest.fixture
def mock_repository():
    """Create mock email delivery repository."""
    repo = AsyncMock()
    
    # Setup default mock delivery
    mock_delivery = EmailDelivery(
        id=str(uuid4()),
        notification_id=str(uuid4()),
        user_id="user-123",
        recipient_email="user@example.com",
        subject="Test",
        provider="smtp",
        status="pending"
    )
    
    repo.create.return_value = mock_delivery
    repo.get_by_id.return_value = mock_delivery
    repo.increment_attempt.return_value = mock_delivery
    repo.update_status.return_value = mock_delivery
    
    return repo


@pytest.fixture
def mock_api_client():
    """Create mock external API client."""
    client = AsyncMock()
    
    # Default user preferences
    client.get_user_preferences.return_value = UserPreferences(
        email_enabled=True,
        push_enabled=True,
        email="user@example.com"
    )
    
    # Default template render
    client.render_template.return_value = TemplateRenderResponse(
        subject="Test Email",
        body_html="<h1>Test</h1>",
        body_text="Test"
    )
    
    # Default status update
    client.update_notification_status.return_value = True
    
    return client


@pytest.fixture
def mock_email_provider():
    """Create mock email provider."""
    provider = AsyncMock()
    provider.get_provider_name.return_value = "smtp"
    provider.send.return_value = SendResult(
        success=True,
        message_id="msg-123",
        provider="smtp"
    )
    return provider


@pytest.fixture
def email_service(mock_repository, mock_api_client):
    """Create email service instance."""
    with patch('app.services.email_service.settings') as mock_settings:
        mock_settings.EMAIL_PROVIDER = "smtp"
        mock_settings.EMAIL_FROM_ADDRESS = "noreply@example.com"
        mock_settings.EMAIL_FROM_NAME = "Test System"
        mock_settings.MAX_RETRY_ATTEMPTS = 3
        mock_settings.RETRY_MULTIPLIER = 1
        mock_settings.RETRY_MIN_WAIT = 1
        mock_settings.RETRY_MAX_WAIT = 10
        mock_settings.CIRCUIT_BREAKER_FAIL_MAX = 5
        mock_settings.CIRCUIT_BREAKER_TIMEOUT = 60
        
        service = EmailService(mock_repository, mock_api_client)
        yield service


@pytest.fixture
def queue_message():
    """Create sample queue message."""
    from datetime import datetime
    return QueueMessage(
        notification_id=str(uuid4()),
        user_id=str(uuid4()),  # Use proper UUID
        template_id=str(uuid4()),  # Use proper UUID
        variables={"name": "John"},
        extra_data={"campaign": "onboarding"},  # Changed from metadata to extra_data
        request_id=str(uuid4()),  # Add required field
        created_at=datetime.utcnow()  # Add required field
    )


class TestEmailService:
    """Test suite for email service."""
    
    @pytest.mark.asyncio
    async def test_process_email_notification_success(
        self,
        email_service,
        queue_message,
        mock_repository,
        mock_api_client,
        mock_email_provider
    ):
        """Test successful email processing end-to-end."""
        # Mock provider creation
        email_service.email_provider = mock_email_provider
        
        result = await email_service.process_email_notification(queue_message)
        
        assert result is True
        
        # Verify workflow steps
        mock_api_client.get_user_preferences.assert_called_once_with(queue_message.user_id)
        mock_api_client.render_template.assert_called_once_with(
            queue_message.template_id,
            {"name": "John"}
        )
        mock_repository.create.assert_called_once()
        mock_email_provider.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_email_user_preferences_not_found(
        self,
        email_service,
        queue_message,
        mock_api_client
    ):
        """Test handling when user preferences cannot be fetched."""
        mock_api_client.get_user_preferences.return_value = None
        
        result = await email_service.process_email_notification(queue_message)
        
        assert result is False
        mock_api_client.update_notification_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_email_disabled_for_user(
        self,
        email_service,
        queue_message,
        mock_api_client,
        mock_repository
    ):
        """Test when email is disabled for user."""
        mock_api_client.get_user_preferences.return_value = UserPreferences(
            email_enabled=False,
            push_enabled=True,
            email="user@example.com"
        )
        
        result = await email_service.process_email_notification(queue_message)
        
        # Should be True (successfully skipped)
        assert result is True
        
        # Should not create delivery or send email
        mock_repository.create.assert_not_called()
        mock_api_client.update_notification_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_email_no_email_address(
        self,
        email_service,
        queue_message,
        mock_api_client
    ):
        """Test when user has no email address."""
        mock_api_client.get_user_preferences.return_value = {
            "email_enabled": True,
            "email": None
        }
        
        result = await email_service.process_email_notification(queue_message)
        
        assert result is False
        mock_api_client.update_notification_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_email_template_rendering_failed(
        self,
        email_service,
        queue_message,
        mock_api_client,
        mock_repository
    ):
        """Test when template rendering fails."""
        mock_api_client.render_template.return_value = None
        
        result = await email_service.process_email_notification(queue_message)
        
        assert result is False
        
        # Should not create delivery or send email
        mock_repository.create.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_email_with_retry_success_first_attempt(
        self,
        email_service,
        mock_repository,
        mock_email_provider
    ):
        """Test successful email send on first attempt."""
        email_service.email_provider = mock_email_provider
        
        with patch('app.services.email_service.email_provider_breaker') as mock_cb:
            mock_cb.call_async = AsyncMock(return_value=SendResult(
                success=True,
                message_id="msg-123",
                provider="smtp"
            ))
            
            result = await email_service._send_email_with_retry(
                delivery_id=uuid4(),
                recipient_email="user@example.com",
                subject="Test",
                body_html="<p>Test</p>",
                body_text="Test"
            )
            
            assert result is True
            mock_repository.increment_attempt.assert_called_once()
            mock_repository.update_status.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_email_with_retry_failure_then_success(
        self,
        email_service,
        mock_repository,
        mock_email_provider
    ):
        """Test email send succeeds after retry."""
        email_service.email_provider = mock_email_provider
        
        # First attempt fails, second succeeds
        mock_email_provider.send.side_effect = [
            SendResult(success=False, error="Temporary error", provider="smtp"),
            SendResult(success=True, message_id="msg-123", provider="smtp")
        ]
        
        with patch('app.services.email_service.email_provider_breaker') as mock_cb:
            async def call_side_effect(func):
                return await func()
            mock_cb.call_async = call_side_effect
            
            result = await email_service._send_email_with_retry(
                delivery_id=uuid4(),
                recipient_email="user@example.com",
                subject="Test",
                body_html="<p>Test</p>",
                body_text="Test"
            )
            
            assert result is True
            # Should increment attempt twice
            assert mock_repository.increment_attempt.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_send_email_circuit_breaker_open(
        self,
        email_service,
        mock_repository
    ):
        """Test behavior when circuit breaker is open."""
        from app.utils.circuit_breaker import CircuitBreakerError
        
        with patch('app.services.email_service.email_provider_breaker') as mock_cb:
            mock_cb.call_async = AsyncMock(side_effect=CircuitBreakerError("Circuit breaker open"))
            
            result = await email_service._send_email_with_retry(
                delivery_id=uuid4(),
                recipient_email="user@example.com",
                subject="Test",
                body_html="<p>Test</p>",
                body_text="Test"
            )
            
            assert result is False
            # Should update status to failed
            mock_repository.update_status.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_email_max_retries_exceeded(
        self,
        email_service,
        mock_repository,
        mock_email_provider
    ):
        """Test behavior when max retries are exceeded."""
        from tenacity import RetryError
        
        email_service.email_provider = mock_email_provider
        
        # Always fail
        mock_email_provider.send.return_value = SendResult(
            success=False,
            error="Permanent error",
            provider="smtp"
        )
        
        with patch('app.services.email_service.email_provider_breaker') as mock_cb:
            async def call_side_effect(func):
                return await func()
            mock_cb.call_async = call_side_effect
            
            # Should raise RetryError after exhausting retries
            with pytest.raises(RetryError):
                await email_service._send_email_with_retry(
                    delivery_id=uuid4(),
                    recipient_email="user@example.com",
                    subject="Test",
                    body_html="<p>Test</p>",
                    body_text="Test"
                )
    
    @pytest.mark.asyncio
    async def test_handle_webhook_delivered(
        self,
        email_service,
        mock_repository,
        mock_api_client
    ):
        """Test handling delivered webhook event."""
        mock_delivery = EmailDelivery(
            id=str(uuid4()),
            notification_id=str(uuid4()),
            user_id="user-123",
            recipient_email="user@example.com",
            subject="Test",
            provider="sendgrid",
            status="sent"
        )
        
        mock_repository.get_by_provider_message_id.return_value = mock_delivery
        
        result = await email_service.handle_webhook(
            provider_message_id="msg-123",
            event="delivered",
            timestamp=int(datetime.utcnow().timestamp())
        )
        
        assert result is True
        
        # Verify status was updated to delivered
        call_args = mock_repository.update_status.call_args
        assert "delivered" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_handle_webhook_bounce(
        self,
        email_service,
        mock_repository
    ):
        """Test handling bounce webhook event."""
        mock_delivery = EmailDelivery(
            id=str(uuid4()),
            notification_id=str(uuid4()),
            user_id="user-123",
            recipient_email="user@example.com",
            subject="Test",
            provider="sendgrid",
            status="sent"
        )
        
        mock_repository.get_by_provider_message_id.return_value = mock_delivery
        
        result = await email_service.handle_webhook(
            provider_message_id="msg-123",
            event="bounce",
            timestamp=int(datetime.utcnow().timestamp())
        )
        
        assert result is True
        
        # Verify status was updated to bounced
        call_args = mock_repository.update_status.call_args
        assert "bounced" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_handle_webhook_delivery_not_found(
        self,
        email_service,
        mock_repository
    ):
        """Test webhook handling when delivery is not found."""
        mock_repository.get_by_provider_message_id.return_value = None
        
        result = await email_service.handle_webhook(
            provider_message_id="non-existent",
            event="delivered",
            timestamp=int(datetime.utcnow().timestamp())
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_handle_webhook_unknown_event(
        self,
        email_service,
        mock_repository
    ):
        """Test handling unknown webhook event."""
        mock_delivery = EmailDelivery(
            id=str(uuid4()),
            notification_id=str(uuid4()),
            user_id="user-123",
            recipient_email="user@example.com",
            subject="Test",
            provider="sendgrid",
            status="sent"
        )
        
        mock_repository.get_by_provider_message_id.return_value = mock_delivery
        
        result = await email_service.handle_webhook(
            provider_message_id="msg-123",
            event="unknown_event",
            timestamp=int(datetime.utcnow().timestamp())
        )
        
        assert result is True
        
        # Should default to "pending" for unknown events
        call_args = mock_repository.update_status.call_args
        assert "pending" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_process_email_unexpected_error(
        self,
        email_service,
        queue_message,
        mock_api_client
    ):
        """Test handling of unexpected errors during processing."""
        mock_api_client.get_user_preferences.side_effect = Exception("Database error")
        
        result = await email_service.process_email_notification(queue_message)
        
        assert result is False
        mock_api_client.update_notification_status.assert_called_once()
    
    def test_create_email_provider_smtp(self):
        """Test SMTP provider creation."""
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.EMAIL_PROVIDER = "smtp"
            mock_settings.CIRCUIT_BREAKER_FAIL_MAX = 5
            mock_settings.CIRCUIT_BREAKER_TIMEOUT = 60
            
            service = EmailService(
                repository=AsyncMock(),
                api_client=AsyncMock()
            )
            
            assert service.email_provider.get_provider_name() == "smtp"
    
    def test_create_email_provider_sendgrid(self):
        """Test SendGrid provider creation."""
        with patch('app.services.email_service.settings') as mock_settings:
            mock_settings.EMAIL_PROVIDER = "sendgrid"
            mock_settings.CIRCUIT_BREAKER_FAIL_MAX = 5
            mock_settings.CIRCUIT_BREAKER_TIMEOUT = 60
            
            service = EmailService(
                repository=AsyncMock(),
                api_client=AsyncMock()
            )
            
            assert service.email_provider.get_provider_name() == "sendgrid"
