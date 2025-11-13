"""
Integration tests for Redis cache utilities.
"""

import pytest
from unittest.mock import AsyncMock, patch, Mock
import json

from app.utils.cache import CacheClient, cache


class TestCacheIntegration:
    """Integration tests for cache client."""
    
    @pytest.mark.asyncio
    async def test_cache_connect_success(self):
        """Test cache connect with mocked Redis."""
        cache_client = CacheClient(ttl=300)
        
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock(return_value=True)
            mock_redis.return_value = mock_client
            
            await cache_client.connect()
            
            assert cache_client.redis_client is not None
            mock_redis.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_disconnect(self):
        """Test cache disconnect."""
        cache_client = CacheClient(ttl=300)
        cache_client.redis_client = AsyncMock()
        cache_client.redis_client.close = AsyncMock()
        
        await cache_client.disconnect()
        
        cache_client.redis_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_get_success(self):
        """Test cache get operation."""
        cache_client = CacheClient(ttl=300)
        mock_redis = AsyncMock()
        test_data = {"key": "value"}
        mock_redis.get = AsyncMock(return_value=json.dumps(test_data))
        cache_client.redis_client = mock_redis
        
        result = await cache_client.get("test_key")
        
        assert result == test_data
        mock_redis.get.assert_called_once_with("test_key")
    
    @pytest.mark.asyncio
    async def test_cache_get_miss(self):
        """Test cache get with cache miss."""
        cache_client = CacheClient(ttl=300)
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        cache_client.redis_client = mock_redis
        
        result = await cache_client.get("missing_key")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_cache_set_success(self):
        """Test cache set operation."""
        cache_client = CacheClient(ttl=300)
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(return_value=True)
        cache_client.redis_client = mock_redis
        
        test_data = {"key": "value"}
        result = await cache_client.set("test_key", test_data, ttl=600)
        
        assert result is True
        mock_redis.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_delete_success(self):
        """Test cache delete operation."""
        cache_client = CacheClient(ttl=300)
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=1)
        cache_client.redis_client = mock_redis
        
        result = await cache_client.delete("test_key")
        
        assert result is True
        mock_redis.delete.assert_called_once_with("test_key")
    
    @pytest.mark.asyncio
    async def test_cache_exists_key_found(self):
        """Test cache exists when key exists."""
        cache_client = CacheClient(ttl=300)
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=1)
        cache_client.redis_client = mock_redis
        
        result = await cache_client.exists("test_key")
        
        assert result is True
        mock_redis.exists.assert_called_once_with("test_key")
    
    @pytest.mark.asyncio
    async def test_cache_exists_key_not_found(self):
        """Test cache exists when key doesn't exist."""
        cache_client = CacheClient(ttl=300)
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        cache_client.redis_client = mock_redis
        
        result = await cache_client.exists("missing_key")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cache_operations_without_connection(self):
        """Test cache operations fail gracefully without connection."""
        cache_client = CacheClient(ttl=300)
        cache_client.redis_client = None
        
        # All operations should return None/False without raising
        assert await cache_client.get("key") is None
        assert await cache_client.set("key", "value") is False
        assert await cache_client.delete("key") is False
        assert await cache_client.exists("key") is False
    
    @pytest.mark.asyncio
    async def test_global_cache_instance(self):
        """Test global cache instance exists."""
        assert cache is not None
        assert isinstance(cache, CacheClient)
        assert cache.default_ttl == 3600
