"""
Unit tests for health check route.
"""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routes.health import health_check
from app.schemas.common import HealthCheckResponse


class TestHealthCheckRoute:
    """Unit tests for health check endpoint."""
    
    @pytest.mark.asyncio
    async def test_health_check_all_services_healthy(self):
        """Test health check when all services are healthy."""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_db.execute.return_value = mock_result
        
        with patch('app.api.v1.routes.health.aio_pika.connect_robust') as mock_rabbitmq, \
             patch('app.api.v1.routes.health.cache') as mock_cache:
            
            # Mock RabbitMQ connection
            mock_connection = AsyncMock()
            mock_rabbitmq.return_value = mock_connection
            
            # Mock Redis cache
            mock_cache.redis_client = AsyncMock()
            mock_cache.redis_client.ping = AsyncMock()
            mock_cache.connect = AsyncMock()
            
            # Call health check
            response = await health_check(db=mock_db)
            
            # Verify response
            assert response.success is True
            assert response.data.status == "healthy"
            assert response.data.database == "connected"
            assert response.data.rabbitmq == "connected"
            assert response.data.redis == "connected"
            assert response.data.service == "email-service"
            assert response.data.version == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_health_check_database_failure(self):
        """Test health check when database is down."""
        # Mock database session that fails
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute.side_effect = Exception("Database connection failed")
        
        with patch('app.api.v1.routes.health.aio_pika.connect_robust') as mock_rabbitmq, \
             patch('app.api.v1.routes.health.cache') as mock_cache, \
             patch('app.api.v1.routes.health.logger') as mock_logger:
            
            # Mock RabbitMQ connection (healthy)
            mock_connection = AsyncMock()
            mock_rabbitmq.return_value = mock_connection
            
            # Mock Redis cache (healthy)
            mock_cache.redis_client = AsyncMock()
            mock_cache.redis_client.ping = AsyncMock()
            mock_cache.connect = AsyncMock()
            
            # Call health check
            response = await health_check(db=mock_db)
            
            # Verify response
            assert response.success is False
            assert response.data.status == "unhealthy"
            assert response.data.database == "disconnected"
            assert response.data.rabbitmq == "connected"
            assert response.data.redis == "connected"
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_rabbitmq_failure(self):
        """Test health check when RabbitMQ is down."""
        # Mock database session (healthy)
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_db.execute.return_value = mock_result
        
        with patch('app.api.v1.routes.health.aio_pika.connect_robust') as mock_rabbitmq, \
             patch('app.api.v1.routes.health.cache') as mock_cache, \
             patch('app.api.v1.routes.health.logger') as mock_logger:
            
            # Mock RabbitMQ connection failure
            mock_rabbitmq.side_effect = Exception("Connection refused")
            
            # Mock Redis cache (healthy)
            mock_cache.redis_client = AsyncMock()
            mock_cache.redis_client.ping = AsyncMock()
            mock_cache.connect = AsyncMock()
            
            # Call health check
            response = await health_check(db=mock_db)
            
            # Verify response
            assert response.success is False
            assert response.data.status == "unhealthy"
            assert response.data.database == "connected"
            assert response.data.rabbitmq == "disconnected"
            assert response.data.redis == "connected"
    
    @pytest.mark.asyncio
    async def test_health_check_redis_failure(self):
        """Test health check when Redis is down."""
        # Mock database session (healthy)
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_db.execute.return_value = mock_result
        
        with patch('app.api.v1.routes.health.aio_pika.connect_robust') as mock_rabbitmq, \
             patch('app.api.v1.routes.health.cache') as mock_cache, \
             patch('app.api.v1.routes.health.logger') as mock_logger:
            
            # Mock RabbitMQ connection (healthy)
            mock_connection = AsyncMock()
            mock_rabbitmq.return_value = mock_connection
            
            # Mock Redis cache failure
            mock_cache.redis_client = None
            mock_cache.connect = AsyncMock()
            
            # Call health check
            response = await health_check(db=mock_db)
            
            # Verify response - Redis failure makes status "degraded"
            assert response.success is True  # Still returns success but degraded
            assert response.data.status == "degraded"
            assert response.data.database == "connected"
            assert response.data.rabbitmq == "connected"
            assert response.data.redis == "disconnected"
    
    @pytest.mark.asyncio
    async def test_health_check_redis_ping_failure(self):
        """Test health check when Redis ping fails."""
        # Mock database session (healthy)
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = Mock()
        mock_db.execute.return_value = mock_result
        
        with patch('app.api.v1.routes.health.aio_pika.connect_robust') as mock_rabbitmq, \
             patch('app.api.v1.routes.health.cache') as mock_cache, \
             patch('app.api.v1.routes.health.logger') as mock_logger:
            
            # Mock RabbitMQ connection (healthy)
            mock_connection = AsyncMock()
            mock_rabbitmq.return_value = mock_connection
            
            # Mock Redis cache with ping failure
            mock_cache.redis_client = AsyncMock()
            mock_cache.redis_client.ping = AsyncMock(side_effect=Exception("Redis error"))
            mock_cache.connect = AsyncMock()
            
            # Call health check
            response = await health_check(db=mock_db)
            
            # Verify response
            assert response.success is True
            assert response.data.status == "degraded"
            assert response.data.redis == "disconnected"
    
    @pytest.mark.asyncio
    async def test_health_check_multiple_services_down(self):
        """Test health check when multiple services are down."""
        # Mock database session that fails
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute.side_effect = Exception("Database error")
        
        with patch('app.api.v1.routes.health.aio_pika.connect_robust') as mock_rabbitmq, \
             patch('app.api.v1.routes.health.cache') as mock_cache:
            
            # Mock RabbitMQ connection failure
            mock_rabbitmq.side_effect = Exception("RabbitMQ error")
            
            # Mock Redis cache failure
            mock_cache.redis_client = None
            mock_cache.connect = AsyncMock()
            
            # Call health check
            response = await health_check(db=mock_db)
            
            # Verify response - degraded (not unhealthy) when only DB and RabbitMQ down but not both critical
            assert response.success is True  # Returns success for degraded
            assert response.data.status == "degraded"
            assert response.data.database == "disconnected"
            assert response.data.rabbitmq == "disconnected"
            assert response.data.redis == "disconnected"
    
    @pytest.mark.asyncio
    async def test_health_check_database_returns_none(self):
        """Test health check when database query returns None."""
        # Mock database session that returns None
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute.return_value = None
        
        with patch('app.api.v1.routes.health.aio_pika.connect_robust') as mock_rabbitmq, \
             patch('app.api.v1.routes.health.cache') as mock_cache:
            
            # Mock RabbitMQ connection (healthy)
            mock_connection = AsyncMock()
            mock_rabbitmq.return_value = mock_connection
            
            # Mock Redis cache (healthy)
            mock_cache.redis_client = AsyncMock()
            mock_cache.redis_client.ping = AsyncMock()
            mock_cache.connect = AsyncMock()
            
            # Call health check
            response = await health_check(db=mock_db)
            
            # Verify response
            assert response.success is True
            assert response.data.status == "degraded"
            assert response.data.database == "error"
