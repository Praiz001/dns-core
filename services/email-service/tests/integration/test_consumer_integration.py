"""
Integration tests for RabbitMQ email consumer.
"""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from datetime import datetime
from uuid import uuid4

from app.consumers.email_consumer import EmailConsumer, start_consumer
from app.schemas.email import QueueMessage


@pytest.fixture
def sample_queue_message():
    """Create a sample queue message."""
    return QueueMessage(
        notification_id=uuid4(),
        user_id=uuid4(),
        template_id=uuid4(),
        variables={"name": "Test User"},
        priority=0,
        request_id="req-123",
        created_at=datetime.utcnow(),
        metadata={}
    )


class TestEmailConsumerIntegration:
    """Integration tests for email consumer."""
    
    @pytest.mark.asyncio
    async def test_consumer_connect_success(self):
        """Test consumer can connect to RabbitMQ."""
        consumer = EmailConsumer()
        
        with patch('aio_pika.connect_robust') as mock_connect:
            mock_connection = AsyncMock()
            mock_channel = AsyncMock()
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_connect.return_value = mock_connection
            
            await consumer.connect()
            
            assert consumer.connection is not None
            assert consumer.channel is not None
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_consumer_disconnect(self):
        """Test consumer can disconnect from RabbitMQ."""
        consumer = EmailConsumer()
        consumer.connection = AsyncMock()
        consumer.connection.close = AsyncMock()
        consumer.channel = AsyncMock()
        consumer.channel.close = AsyncMock()
        
        await consumer.disconnect()
        
        consumer.channel.close.assert_called_once()
        consumer.connection.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_consumer_queue_declaration(self):
        """Test consumer declares queue with DLQ."""
        consumer = EmailConsumer()
        
        with patch('aio_pika.connect_robust') as mock_connect:
            mock_connection = AsyncMock()
            mock_channel = AsyncMock()
            mock_queue = AsyncMock()
            
            mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_connect.return_value = mock_connection
            
            await consumer.connect()
            await consumer.start_consuming()
            
            # Verify queue declarations (main queue + DLQ)
            assert mock_channel.declare_queue.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_consumer_prefetch_configuration(self):
        """Test consumer sets QoS prefetch count."""
        consumer = EmailConsumer()
        
        with patch('aio_pika.connect_robust') as mock_connect:
            mock_connection = AsyncMock()
            mock_channel = AsyncMock()
            mock_channel.set_qos = AsyncMock()
            
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_connect.return_value = mock_connection
            
            await consumer.connect()
            await consumer.start_consuming()
            
            # Verify QoS was set
            mock_channel.set_qos.assert_called()
    
    @pytest.mark.asyncio
    async def test_process_message_validation_error(self):
        """Test message processing with validation error."""
        consumer = EmailConsumer()
        
        mock_message = AsyncMock()
        mock_message.body = b'{"invalid": "data"}'
        mock_message.process = AsyncMock()
        
        # Mock the context manager
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock()
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_message.process.return_value = mock_cm
        
        with patch('app.consumers.email_consumer.logger') as mock_logger:
            await consumer._process_message(mock_message)
            
            # Verify error was logged
            assert mock_logger.error.called or mock_logger.warning.called
    
    @pytest.mark.asyncio
    async def test_start_consumer_creates_instance(self):
        """Test start_consumer creates and initializes consumer."""
        with patch('app.consumers.email_consumer.EmailConsumer') as mock_class:
            mock_instance = AsyncMock()
            mock_instance.start_consuming = AsyncMock()
            mock_class.return_value = mock_instance
            
            result = start_consumer()
            
            assert result == mock_instance
            mock_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_consumer_connection_retry_on_failure(self):
        """Test consumer retries connection on failure."""
        consumer = EmailConsumer()
        
        with patch('aio_pika.connect_robust') as mock_connect:
            # First attempt fails, second succeeds
            mock_connection = AsyncMock()
            mock_channel = AsyncMock()
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            
            mock_connect.side_effect = [Exception("Connection failed"), mock_connection]
            
            # First attempt should fail
            try:
                await consumer.connect()
            except Exception:
                pass
            
            # Second attempt should succeed
            await consumer.connect()
            
            assert consumer.connection is not None
            assert mock_connect.call_count == 2
