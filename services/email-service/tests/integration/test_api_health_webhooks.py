"""
Integration tests for API health and webhook endpoints.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, Mock

from app.main import app


@pytest.fixture
async def client():
    """Create async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    """Integration tests for health check endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test health check endpoint returns 200."""
        with patch('app.db.session.engine') as mock_engine, \
             patch('aio_pika.connect_robust') as mock_rabbitmq, \
             patch('app.utils.cache.cache.redis_client') as mock_redis:
            
            # Mock database
            mock_connection = AsyncMock()
            mock_engine.connect.return_value.__aenter__.return_value = mock_connection
            
            # Mock RabbitMQ
            mock_conn = AsyncMock()
            mock_conn.close = AsyncMock()
            mock_rabbitmq.return_value = mock_conn
            
            # Mock Redis
            mock_redis.ping = AsyncMock(return_value=True)
            
            response = await client.get("/api/v1/health")
            
            assert response.status_code == 200
            data = response.json()
            assert "success" in data
            assert "data" in data


class TestWebhookEndpoint:
    """Integration tests for email webhook endpoint."""
    
    @pytest.mark.asyncio
    async def test_webhook_test_endpoint(self, client):
        """Test webhook test endpoint."""
        response = await client.get("/api/v1/webhooks/email/test")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Webhook endpoint is working"
    
    @pytest.mark.asyncio
    async def test_webhook_empty_payload(self, client):
        """Test webhook with empty payload."""
        response = await client.post("/api/v1/webhooks/email", json=[])
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "No events to process"
    
    @pytest.mark.asyncio
    async def test_webhook_delivered_event(self, client):
        """Test webhook with delivered event."""
        webhook_data = [{
            "event": "delivered",
            "email": "test@example.com",
            "timestamp": 1234567890,
            "sg_message_id": "test-message-id"
        }]
        
        with patch('app.api.v1.routes.webhooks.logger') as mock_logger:
            response = await client.post("/api/v1/webhooks/email", json=webhook_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            mock_logger.info.assert_called()
