"""
Unit tests for SMTP Email Provider.

Tests cover:
- Successful email sending
- Connection failures
- Authentication failures
- SMTP exceptions
- TLS configuration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import smtplib

from app.providers.smtp import SMTPProvider
from app.providers.base import EmailMessage, SendResult


@pytest.fixture
def smtp_provider():
    """Create SMTP provider instance."""
    with patch('app.providers.smtp.settings') as mock_settings:
        mock_settings.SMTP_HOST = "smtp.example.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USERNAME = "test@example.com"
        mock_settings.SMTP_PASSWORD = "password"
        mock_settings.SMTP_USE_TLS = True
        mock_settings.EMAIL_FROM_ADDRESS = "noreply@example.com"
        mock_settings.EMAIL_FROM_NAME = "Test System"
        
        provider = SMTPProvider()
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


class TestSMTPProvider:
    """Test suite for SMTP provider."""
    
    @pytest.mark.asyncio
    async def test_send_email_success(self, smtp_provider, email_message):
        """Test successful email sending."""
        with patch('smtplib.SMTP') as mock_smtp:
            # Setup mock
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            # Execute
            result = await smtp_provider.send(email_message)
            
            # Assert
            assert result.success is True
            assert result.provider == "smtp"
            assert result.error is None
            
            # Verify SMTP calls
            mock_smtp.assert_called_once_with("smtp.example.com", 587)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("test@example.com", "password")
            mock_server.send_message.assert_called_once()
            mock_server.quit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_with_custom_from(self, smtp_provider):
        """Test email with custom from address."""
        message = EmailMessage(
            to="recipient@example.com",
            subject="Test",
            body_html="<p>Test</p>",
            body_text="Test",
            from_email="custom@example.com",
            from_name="Custom Sender"
        )
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            result = await smtp_provider.send(message)
            
            assert result.success is True
            # Verify message was sent
            mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_with_reply_to(self, smtp_provider):
        """Test email with reply-to header."""
        message = EmailMessage(
            to="recipient@example.com",
            subject="Test",
            body_html="<p>Test</p>",
            body_text="Test",
            reply_to="reply@example.com"
        )
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            result = await smtp_provider.send(message)
            
            assert result.success is True
    
    @pytest.mark.asyncio
    async def test_send_email_connection_error(self, smtp_provider, email_message):
        """Test handling of connection errors."""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = smtplib.SMTPConnectError(421, "Connection refused")
            
            result = await smtp_provider.send(email_message)
            
            assert result.success is False
            assert result.provider == "smtp"
            assert "SMTP error" in result.error
    
    @pytest.mark.asyncio
    async def test_send_email_authentication_error(self, smtp_provider, email_message):
        """Test handling of authentication errors."""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, "Authentication failed")
            
            result = await smtp_provider.send(email_message)
            
            assert result.success is False
            assert "SMTP error" in result.error
    
    @pytest.mark.asyncio
    async def test_send_email_recipient_error(self, smtp_provider, email_message):
        """Test handling of recipient errors."""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            mock_server.send_message.side_effect = smtplib.SMTPRecipientsRefused({
                email_message.to: (550, "User not found")
            })
            
            result = await smtp_provider.send(email_message)
            
            assert result.success is False
            assert "SMTP error" in result.error
    
    @pytest.mark.asyncio
    async def test_send_email_unexpected_error(self, smtp_provider, email_message):
        """Test handling of unexpected errors."""
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = Exception("Unexpected error")
            
            result = await smtp_provider.send(email_message)
            
            assert result.success is False
            assert "Unexpected error" in result.error
    
    @pytest.mark.asyncio
    async def test_send_email_ssl_mode(self, email_message):
        """Test SMTP with SSL instead of TLS."""
        with patch('app.providers.smtp.settings') as mock_settings:
            mock_settings.SMTP_HOST = "smtp.example.com"
            mock_settings.SMTP_PORT = 465
            mock_settings.SMTP_USERNAME = "test@example.com"
            mock_settings.SMTP_PASSWORD = "password"
            mock_settings.SMTP_USE_TLS = False
            mock_settings.EMAIL_FROM_ADDRESS = "noreply@example.com"
            mock_settings.EMAIL_FROM_NAME = "Test System"
            
            provider = SMTPProvider()
            
            with patch('smtplib.SMTP_SSL') as mock_smtp_ssl:
                mock_server = MagicMock()
                mock_smtp_ssl.return_value = mock_server
                
                result = await provider.send(email_message)
                
                assert result.success is True
                mock_smtp_ssl.assert_called_once_with("smtp.example.com", 465)
    
    @pytest.mark.asyncio
    async def test_send_email_text_only(self, smtp_provider):
        """Test sending email with text only (no HTML)."""
        message = EmailMessage(
            to="recipient@example.com",
            subject="Test",
            body_text="Plain text email"
        )
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            
            result = await smtp_provider.send(message)
            
            assert result.success is True
    
    def test_get_provider_name(self, smtp_provider):
        """Test provider name."""
        assert smtp_provider.get_provider_name() == "smtp"
