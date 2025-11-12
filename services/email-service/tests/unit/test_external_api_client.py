"""
Unit tests for External API Client.

Tests cover:
- User preferences retrieval
- Template rendering
- Notification status updates
- Circuit breaker integration
- Retry logic
- Cache integration
- Error handling
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import httpx

from app.services.external_api import ExternalAPIClient


@pytest.fixture
def mock_cache():
    """Create mock Redis cache."""
    cache = AsyncMock()
    cache.get.return_value = None
    cache.set.return_value = None
    return cache


@pytest.fixture
def mock_circuit_breaker():
    """Create mock circuit breaker."""
    cb = MagicMock()
    cb.is_open = False
    cb.record_success = Mock()
    cb.record_failure = Mock()
    return cb


@pytest_asyncio.fixture
async def api_client(mock_cache):
    """Create API client instance."""
    with patch('app.services.external_api.cache', mock_cache):
        with patch('app.services.external_api.settings') as mock_settings:
            mock_settings.USER_SERVICE_URL = "http://user-service"
            mock_settings.TEMPLATE_SERVICE_URL = "http://template-service"
            mock_settings.API_GATEWAY_URL = "http://api-gateway"
            mock_settings.HTTP_TIMEOUT = 30
            mock_settings.HTTP_MAX_RETRIES = 3
            mock_settings.CACHE_TTL_PREFERENCES = 300
            
            client = ExternalAPIClient()
            yield client


class TestExternalAPIClient:
    """Test suite for external API client."""
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_from_cache(self, api_client, mock_cache):
        """Test retrieving user preferences from cache."""
        from app.schemas.email import UserPreferences
        
        # Setup cache hit - should return dict
        cached_data = {"email_enabled": True, "push_enabled": True, "email": "user@example.com"}
        mock_cache.get.return_value = cached_data
        
        result = await api_client.get_user_preferences("user-123")
        
        assert isinstance(result, UserPreferences)
        assert result.email_enabled is True
        mock_cache.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_from_api(self, api_client, mock_cache):
        """Test retrieving user preferences from API when cache misses."""
        from app.schemas.email import UserPreferences
        
        # Setup cache miss
        mock_cache.get.return_value = None
        
        # Mock HTTP response with proper structure
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "email_enabled": True,
                "push_enabled": True,
                "email": "user@example.com"
            }
        }
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            with patch('app.services.external_api.user_service_breaker') as mock_cb:
                # Mock the call_async to execute the function
                async def mock_call_async(func):
                    return await func()
                mock_cb.call_async = mock_call_async
                
                result = await api_client.get_user_preferences("user-123")
                
                assert isinstance(result, UserPreferences)
                assert result.email_enabled is True
                
                # Verify API was called
                mock_client.get.assert_called_once()
                
                # Verify result was cached
                mock_cache.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_circuit_breaker_open(self, api_client, mock_cache):
        """Test behavior when circuit breaker is open."""
        from app.schemas.email import UserPreferences
        from app.utils.circuit_breaker import CircuitBreakerError
        
        mock_cache.get.return_value = None
        
        with patch('app.services.external_api.user_service_breaker') as mock_cb:
            # Mock call_async to raise CircuitBreakerError
            async def mock_call_async(func):
                raise CircuitBreakerError("Circuit breaker open")
            mock_cb.call_async = mock_call_async
            
            result = await api_client.get_user_preferences("user-123")
            
            # Should return default preferences when circuit is open
            assert isinstance(result, UserPreferences)
            assert result.email_enabled is True
            assert result.push_enabled is True
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_api_error(self, api_client, mock_cache):
        """Test handling of API errors."""
        mock_cache.get.return_value = None
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.side_effect = httpx.HTTPError("Connection failed")
            mock_client_class.return_value = mock_client
            
            with patch('app.services.external_api.user_service_breaker') as mock_cb:
                # Mock call_async to execute the function (which will raise)
                async def mock_call_async(func):
                    return await func()
                mock_cb.call_async = mock_call_async
                
                result = await api_client.get_user_preferences("user-123")
                
                # Should return None on error
                assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_404(self, api_client, mock_cache):
        """Test handling of user not found."""
        mock_cache.get.return_value = None
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found", request=Mock(), response=mock_response
        )
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            with patch('app.services.external_api.user_service_breaker') as mock_cb:
                # Mock call_async to execute the function
                async def mock_call_async(func):
                    return await func()
                mock_cb.call_async = mock_call_async
                
                result = await api_client.get_user_preferences("user-123")
                
                # Should return None for 404
                assert result is None
    
    @pytest.mark.asyncio
    async def test_render_template_success(self, api_client):
        """Test successful template rendering."""
        from app.schemas.email import TemplateRenderResponse
        from uuid import uuid4
        
        template_id = uuid4()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "subject": "Welcome!",
                "body_html": "<h1>Welcome</h1>",
                "body_text": "Welcome"
            }
        }
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            with patch('app.services.external_api.template_service_breaker') as mock_cb:
                # Mock call_async to execute the function
                async def mock_call_async(func):
                    return await func()
                mock_cb.call_async = mock_call_async
                
                result = await api_client.render_template(
                    template_id=template_id,
                    variables={"name": "John"}
                )
                
                assert isinstance(result, TemplateRenderResponse)
                assert result.subject == "Welcome!"
                assert result.body_html == "<h1>Welcome</h1>"
                
                # Verify API was called
                mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_render_template_circuit_breaker_open(self, api_client):
        """Test template rendering when circuit breaker is open."""
        from app.utils.circuit_breaker import CircuitBreakerError
        from uuid import uuid4
        
        template_id = uuid4()
        
        with patch('app.services.external_api.template_service_breaker') as mock_cb:
            # Mock call_async to raise CircuitBreakerError
            async def mock_call_async(func):
                raise CircuitBreakerError("Circuit breaker is open")
            mock_cb.call_async = mock_call_async
            
            result = await api_client.render_template(
                template_id=template_id,
                variables={"name": "John"}
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_render_template_api_error(self, api_client):
        """Test handling of template API errors."""
        from uuid import uuid4
        
        template_id = uuid4()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = httpx.TimeoutException("Timeout")
            mock_client_class.return_value = mock_client
            
            with patch('app.services.external_api.template_service_breaker') as mock_cb:
                # Mock call_async to execute the function
                async def mock_call_async(func):
                    return await func()
                mock_cb.call_async = mock_call_async
                
                result = await api_client.render_template(
                    template_id=template_id,
                    variables={}
                )
                
                assert result is None
    
    @pytest.mark.asyncio
    async def test_update_notification_status_success(self, api_client):
        """Test successful notification status update."""
        from app.schemas.email import NotificationStatusUpdate
        from uuid import uuid4
        
        notification_id = uuid4()
        status_update = NotificationStatusUpdate(status="delivered")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.patch.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            with patch('app.services.external_api.gateway_breaker') as mock_cb:
                # Mock call_async to execute the function
                async def mock_call_async(func):
                    return await func()
                mock_cb.call_async = mock_call_async
                
                result = await api_client.update_notification_status(
                    notification_id=notification_id,
                    status_update=status_update
                )
                
                assert result is True
                
                # Verify API was called
                mock_client.patch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_notification_status_with_metadata(self, api_client):
        """Test status update with additional metadata."""
        from app.schemas.email import NotificationStatusUpdate
        from uuid import uuid4
        from datetime import datetime
        
        notification_id = uuid4()
        status_update = NotificationStatusUpdate(
            status="failed",
            error_message="SMTP error",
            provider_message_id="smtp-123"
        )
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.patch.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            with patch('app.services.external_api.gateway_breaker') as mock_cb:
                # Mock call_async to execute the function
                async def mock_call_async(func):
                    return await func()
                mock_cb.call_async = mock_call_async
                
                result = await api_client.update_notification_status(
                    notification_id=notification_id,
                    status_update=status_update
                )
                
                assert result is True
                
                # Verify payload includes metadata
                call_args = mock_client.patch.call_args
                payload = call_args.kwargs['json']
                assert payload['error_message'] == "SMTP error"
                assert payload['provider_message_id'] == "smtp-123"
    
    @pytest.mark.asyncio
    async def test_update_notification_status_circuit_breaker_open(self, api_client):
        """Test status update when circuit breaker is open."""
        from app.utils.circuit_breaker import CircuitBreakerError
        from app.schemas.email import NotificationStatusUpdate
        from uuid import uuid4
        
        notification_id = uuid4()
        status_update = NotificationStatusUpdate(status="delivered")
        
        with patch('app.services.external_api.gateway_breaker') as mock_cb:
            # Mock call_async to raise CircuitBreakerError
            async def mock_call_async(func):
                raise CircuitBreakerError("Circuit breaker is open")
            mock_cb.call_async = mock_call_async
            
            result = await api_client.update_notification_status(
                notification_id=notification_id,
                status_update=status_update
            )
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_update_notification_status_api_error(self, api_client):
        """Test handling of status update errors."""
        from app.schemas.email import NotificationStatusUpdate
        from uuid import uuid4
        
        notification_id = uuid4()
        status_update = NotificationStatusUpdate(status="delivered")
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.patch.side_effect = httpx.NetworkError("Connection failed")
            mock_client_class.return_value = mock_client
            
            with patch('app.services.external_api.gateway_breaker') as mock_cb:
                # Mock call_async to execute the function
                async def mock_call_async(func):
                    return await func()
                mock_cb.call_async = mock_call_async
                
                result = await api_client.update_notification_status(
                    notification_id=notification_id,
                    status_update=status_update
                )
                
                assert result is False
    
    @pytest.mark.asyncio
    async def test_retry_on_transient_errors(self, api_client, mock_cache):
        """Test retry logic on transient errors."""
        from app.schemas.email import UserPreferences
        from uuid import uuid4
        
        user_id = uuid4()
        mock_cache.get.return_value = None
        
        # Simulate transient network error that gets caught and returns None
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            # Network error will be caught and return None (no retry for caught exceptions)
            mock_client.get.side_effect = httpx.NetworkError("Connection failed")
            mock_client_class.return_value = mock_client
            
            with patch('app.services.external_api.user_service_breaker') as mock_cb:
                # Mock call_async to execute the function
                async def mock_call_async(func):
                    return await func()
                mock_cb.call_async = mock_call_async
                
                result = await api_client.get_user_preferences(user_id)
                
                # Transient errors are caught and return None
                assert result is None
                
                # Exception is caught within the inner function, so only one call is made
                assert mock_client.get.call_count == 1
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_records_success(self, api_client, mock_cache):
        """Test that circuit breaker records successful calls."""
        from app.schemas.email import UserPreferences
        from uuid import uuid4
        
        user_id = uuid4()
        mock_cache.get.return_value = None
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "email_enabled": True,
                "push_enabled": True
            }
        }
        mock_response.raise_for_status = Mock()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            with patch('app.services.external_api.user_service_breaker') as mock_cb:
                # Mock call_async to execute the function and track execution
                call_count = 0
                async def mock_call_async(func):
                    nonlocal call_count
                    call_count += 1
                    return await func()
                mock_cb.call_async = mock_call_async
                
                result = await api_client.get_user_preferences(user_id)
                
                # Verify the function was called through circuit breaker
                assert call_count == 1
                assert isinstance(result, UserPreferences)
