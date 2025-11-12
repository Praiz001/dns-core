"""
Unit tests for SendGrid Email Provider.

Tests cover:
- Successful email sending
- API errors
- Timeout errors
- Invalid API key
- Network failures
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx

from app.providers.sendgrid import SendGridProvider
from app.providers.base import EmailMessage, SendResult


@pytest.fixture
def sendgrid_provider():
    """Create SendGrid provider instance."""
    with patch('app.providers.sendgrid.settings') as mock_settings:
        mock_settings.SENDGRID_API_KEY = "test-api-key"
        mock_settings.EMAIL_FROM_ADDRESS = "noreply@example.com"
        mock_settings.EMAIL_FROM_NAME = "Test System"
        mock_settings.HTTP_TIMEOUT = 30
        
        provider = SendGridProvider()
        yield provider


@pytest.fixture
def email_message():
    """Create test email message."""
    return EmailMessage(
        to="recipient@example.com",
        subject="Test Email",
        body_html="<h1>Test</h1>",
        body_text="Test",
        from_email="sender@example.com",
        from_name="Test Sender"
    )


class TestSendGridProvider:
    """Test suite for SendGrid provider."""
    
    @pytest.mark.asyncio
    async def test_send_email_success(self, sendgrid_provider, email_message):
        """Test successful email sending via SendGrid."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {"X-Message-Id": "test-message-id-123"}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = await sendgrid_provider.send(email_message)
            
            assert result.success is True
            assert result.message_id == "test-message-id-123"
            assert result.provider == "sendgrid"
            assert result.error is None
    
    @pytest.mark.asyncio
    async def test_send_email_with_reply_to(self, sendgrid_provider):
        """Test email with reply-to header."""
        message = EmailMessage(
            to="recipient@example.com",
            subject="Test",
            body_html="<p>Test</p>",
            body_text="Test",
            reply_to="reply@example.com"
        )
        
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {"X-Message-Id": "test-id"}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = await sendgrid_provider.send(message)
            
            assert result.success is True
            
            # Verify reply-to was included in payload
            call_args = mock_client.post.call_args
            payload = call_args.kwargs['json']
            assert 'reply_to' in payload
            assert payload['reply_to']['email'] == "reply@example.com"
    
    @pytest.mark.asyncio
    async def test_send_email_api_error_400(self, sendgrid_provider, email_message):
        """Test handling of 400 Bad Request error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = '{"errors": [{"message": "Invalid email"}]}'
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = await sendgrid_provider.send(email_message)
            
            assert result.success is False
            assert result.provider == "sendgrid"
            assert "SendGrid API error: 400" in result.error
    
    @pytest.mark.asyncio
    async def test_send_email_unauthorized(self, sendgrid_provider, email_message):
        """Test handling of 401 Unauthorized error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = '{"errors": [{"message": "Unauthorized"}]}'
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = await sendgrid_provider.send(email_message)
            
            assert result.success is False
            assert "401" in result.error
    
    @pytest.mark.asyncio
    async def test_send_email_timeout(self, sendgrid_provider, email_message):
        """Test handling of timeout errors."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
            mock_client_class.return_value = mock_client
            
            result = await sendgrid_provider.send(email_message)
            
            assert result.success is False
            assert "Timeout error" in result.error
    
    @pytest.mark.asyncio
    async def test_send_email_network_error(self, sendgrid_provider, email_message):
        """Test handling of network errors."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.NetworkError("Connection failed")
            mock_client_class.return_value = mock_client
            
            result = await sendgrid_provider.send(email_message)
            
            assert result.success is False
            assert result.provider == "sendgrid"
    
    @pytest.mark.asyncio
    async def test_send_email_unexpected_error(self, sendgrid_provider, email_message):
        """Test handling of unexpected errors."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.side_effect = Exception("Unexpected error")
            mock_client_class.return_value = mock_client
            
            result = await sendgrid_provider.send(email_message)
            
            assert result.success is False
            assert "Unexpected error" in result.error
    
    @pytest.mark.asyncio
    async def test_send_email_text_only(self, sendgrid_provider):
        """Test sending email with text only."""
        message = EmailMessage(
            to="recipient@example.com",
            subject="Test",
            body_text="Plain text email"
        )
        
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {"X-Message-Id": "test-id"}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = await sendgrid_provider.send(message)
            
            assert result.success is True
            
            # Verify only text content was sent
            call_args = mock_client.post.call_args
            payload = call_args.kwargs['json']
            assert len(payload['content']) == 1
            assert payload['content'][0]['type'] == 'text/plain'
    
    @pytest.mark.asyncio
    async def test_send_email_html_and_text(self, sendgrid_provider, email_message):
        """Test sending email with both HTML and text."""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {"X-Message-Id": "test-id"}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = await sendgrid_provider.send(email_message)
            
            assert result.success is True
            
            # Verify both content types were sent
            call_args = mock_client.post.call_args
            payload = call_args.kwargs['json']
            assert len(payload['content']) == 2
    
    @pytest.mark.asyncio
    async def test_send_email_default_from(self, sendgrid_provider):
        """Test using default from address when not specified."""
        message = EmailMessage(
            to="recipient@example.com",
            subject="Test",
            body_text="Test"
        )
        
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.headers = {"X-Message-Id": "test-id"}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            result = await sendgrid_provider.send(message)
            
            assert result.success is True
            
            # Verify default from address was used
            call_args = mock_client.post.call_args
            payload = call_args.kwargs['json']
            assert payload['from']['email'] == "noreply@example.com"
    
    def test_get_provider_name(self, sendgrid_provider):
        """Test provider name."""
        assert sendgrid_provider.get_provider_name() == "sendgrid"
