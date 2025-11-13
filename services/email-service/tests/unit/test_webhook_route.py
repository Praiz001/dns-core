"""
Unit tests for webhook routes.
"""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.api.v1.routes.webhooks import email_webhook, test_webhook
from app.schemas.webhook import SendGridWebhook


class TestWebhookRoutes:
    """Unit tests for webhook endpoints."""
    
    @pytest.mark.asyncio
    async def test_email_webhook_single_event_success(self):
        """Test processing single webhook event successfully."""
        # Create mock webhook event
        event = SendGridWebhook(
            email="test@example.com",
            timestamp=1234567890,
            event="delivered",
            sg_message_id="test-msg-123"
        )
        
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('app.api.v1.routes.webhooks.EmailService') as mock_service_class, \
             patch('app.api.v1.routes.webhooks.EmailDeliveryRepository'), \
             patch('app.api.v1.routes.webhooks.ExternalAPIClient'):
            
            # Mock email service
            mock_service = AsyncMock()
            mock_service.handle_webhook.return_value = True
            mock_service_class.return_value = mock_service
            
            # Call webhook endpoint
            response = await email_webhook(events=[event], db=mock_db)
            
            # Verify response
            assert response.success is True
            assert response.data.received is True
            assert response.data.processed is True
            assert "1 out of 1" in response.data.message
            
            # Verify service was called
            mock_service.handle_webhook.assert_called_once_with(
                provider_message_id="test-msg-123",
                event="delivered",
                timestamp=1234567890
            )
    
    @pytest.mark.asyncio
    async def test_email_webhook_multiple_events(self):
        """Test processing multiple webhook events."""
        # Create mock webhook events
        events = [
            SendGridWebhook(
                email=f"test{i}@example.com",
                timestamp=1234567890 + i,
                event="delivered",
                sg_message_id=f"msg-{i}"
            )
            for i in range(3)
        ]
        
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('app.api.v1.routes.webhooks.EmailService') as mock_service_class, \
             patch('app.api.v1.routes.webhooks.EmailDeliveryRepository'), \
             patch('app.api.v1.routes.webhooks.ExternalAPIClient'):
            
            # Mock email service
            mock_service = AsyncMock()
            mock_service.handle_webhook.return_value = True
            mock_service_class.return_value = mock_service
            
            # Call webhook endpoint
            response = await email_webhook(events=events, db=mock_db)
            
            # Verify response
            assert response.success is True
            assert response.data.processed is True
            assert "3 out of 3" in response.data.message
            
            # Verify service was called for each event
            assert mock_service.handle_webhook.call_count == 3
    
    @pytest.mark.asyncio
    async def test_email_webhook_partial_failure(self):
        """Test processing webhooks with some failures."""
        # Create mock webhook events
        events = [
            SendGridWebhook(
                email=f"test{i}@example.com",
                timestamp=1234567890 + i,
                event="delivered",
                sg_message_id=f"msg-{i}"
            )
            for i in range(3)
        ]
        
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('app.api.v1.routes.webhooks.EmailService') as mock_service_class, \
             patch('app.api.v1.routes.webhooks.EmailDeliveryRepository'), \
             patch('app.api.v1.routes.webhooks.ExternalAPIClient'), \
             patch('app.api.v1.routes.webhooks.logger') as mock_logger:
            
            # Mock email service - first succeeds, second fails, third succeeds
            mock_service = AsyncMock()
            mock_service.handle_webhook.side_effect = [True, False, True]
            mock_service_class.return_value = mock_service
            
            # Call webhook endpoint
            response = await email_webhook(events=events, db=mock_db)
            
            # Verify response
            assert response.success is True
            assert response.data.received is True
            assert response.data.processed is False  # Not all processed
            assert "2 out of 3" in response.data.message
    
    @pytest.mark.asyncio
    async def test_email_webhook_event_processing_exception(self):
        """Test handling exception during event processing."""
        event = SendGridWebhook(
            email="test@example.com",
            timestamp=1234567890,
            event="delivered",
            sg_message_id="test-msg-123"
        )
        
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('app.api.v1.routes.webhooks.EmailService') as mock_service_class, \
             patch('app.api.v1.routes.webhooks.EmailDeliveryRepository'), \
             patch('app.api.v1.routes.webhooks.ExternalAPIClient'), \
             patch('app.api.v1.routes.webhooks.logger') as mock_logger:
            
            # Mock email service to raise exception
            mock_service = AsyncMock()
            mock_service.handle_webhook.side_effect = Exception("Processing error")
            mock_service_class.return_value = mock_service
            
            # Call webhook endpoint - should not raise, just log error
            response = await email_webhook(events=[event], db=mock_db)
            
            # Verify response
            assert response.success is True
            assert response.data.received is True
            assert response.data.processed is False
            assert "0 out of 1" in response.data.message
            
            # Verify error was logged
            mock_logger.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_email_webhook_empty_events(self):
        """Test webhook with empty events list."""
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('app.api.v1.routes.webhooks.EmailService') as mock_service_class, \
             patch('app.api.v1.routes.webhooks.EmailDeliveryRepository'), \
             patch('app.api.v1.routes.webhooks.ExternalAPIClient'):
            
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Call webhook endpoint with empty list
            response = await email_webhook(events=[], db=mock_db)
            
            # Verify response
            assert response.success is True
            assert response.data.received is True
            assert response.data.processed is True
            assert "0 out of 0" in response.data.message
            
            # Verify service was not called
            mock_service.handle_webhook.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_email_webhook_bounce_event(self):
        """Test processing bounce event."""
        event = SendGridWebhook(
            email="bounce@example.com",
            timestamp=1234567890,
            event="bounce",
            sg_message_id="bounce-msg-123",
            reason="550 5.1.1 User unknown"
        )
        
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('app.api.v1.routes.webhooks.EmailService') as mock_service_class, \
             patch('app.api.v1.routes.webhooks.EmailDeliveryRepository'), \
             patch('app.api.v1.routes.webhooks.ExternalAPIClient'):
            
            mock_service = AsyncMock()
            mock_service.handle_webhook.return_value = True
            mock_service_class.return_value = mock_service
            
            # Call webhook endpoint
            response = await email_webhook(events=[event], db=mock_db)
            
            # Verify response
            assert response.success is True
            
            # Verify bounce event was processed
            mock_service.handle_webhook.assert_called_once_with(
                provider_message_id="bounce-msg-123",
                event="bounce",
                timestamp=1234567890
            )
    
    @pytest.mark.asyncio
    async def test_email_webhook_deferred_event(self):
        """Test processing deferred event."""
        event = SendGridWebhook(
            email="deferred@example.com",
            timestamp=1234567890,
            event="deferred",
            sg_message_id="deferred-msg-123",
            response="451 4.7.1 Please try again later"
        )
        
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('app.api.v1.routes.webhooks.EmailService') as mock_service_class, \
             patch('app.api.v1.routes.webhooks.EmailDeliveryRepository'), \
             patch('app.api.v1.routes.webhooks.ExternalAPIClient'):
            
            mock_service = AsyncMock()
            mock_service.handle_webhook.return_value = True
            mock_service_class.return_value = mock_service
            
            # Call webhook endpoint
            response = await email_webhook(events=[event], db=mock_db)
            
            # Verify response
            assert response.success is True
            
            # Verify deferred event was processed
            mock_service.handle_webhook.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_email_webhook_critical_failure(self):
        """Test webhook endpoint handles critical failures."""
        event = SendGridWebhook(
            email="test@example.com",
            timestamp=1234567890,
            event="delivered",
            sg_message_id="test-msg-123"
        )
        
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('app.api.v1.routes.webhooks.EmailDeliveryRepository') as mock_repo, \
             patch('app.api.v1.routes.webhooks.logger') as mock_logger:
            
            # Mock repository initialization to raise exception
            mock_repo.side_effect = Exception("Database connection failed")
            
            # Call webhook endpoint - should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await email_webhook(events=[event], db=mock_db)
            
            # Verify exception details
            assert exc_info.value.status_code == 500
            assert "Failed to process webhook" in str(exc_info.value.detail)
            
            # Verify error was logged
            assert mock_logger.error.called
    
    @pytest.mark.asyncio
    async def test_test_webhook_endpoint(self):
        """Test the test webhook endpoint."""
        response = await test_webhook()
        
        assert response["message"] == "Email webhook endpoint is active"
        assert response["service"] == "email-service"
    
    @pytest.mark.asyncio
    async def test_email_webhook_logs_received_count(self):
        """Test that webhook logs the number of events received."""
        events = [
            SendGridWebhook(
                email=f"test{i}@example.com",
                timestamp=1234567890,
                event="delivered",
                sg_message_id=f"msg-{i}"
            )
            for i in range(5)
        ]
        
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('app.api.v1.routes.webhooks.EmailService') as mock_service_class, \
             patch('app.api.v1.routes.webhooks.EmailDeliveryRepository'), \
             patch('app.api.v1.routes.webhooks.ExternalAPIClient'), \
             patch('app.api.v1.routes.webhooks.logger') as mock_logger:
            
            mock_service = AsyncMock()
            mock_service.handle_webhook.return_value = True
            mock_service_class.return_value = mock_service
            
            # Call webhook endpoint
            await email_webhook(events=events, db=mock_db)
            
            # Verify logging
            info_calls = [call for call in mock_logger.info.call_args_list]
            
            # Should log received count and processed count
            assert any("Received 5 webhook events" in str(call) for call in info_calls)
            assert any("Processed 5/5 webhook events" in str(call) for call in info_calls)
