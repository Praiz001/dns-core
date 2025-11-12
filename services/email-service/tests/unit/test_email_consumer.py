"""
Unit tests for RabbitMQ email consumer.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, Mock, MagicMock
from datetime import datetime
from uuid import uuid4

from app.consumers.email_consumer import EmailConsumer, start_consumer
from app.schemas.email import QueueMessage


class TestEmailConsumer:
    """Unit tests for EmailConsumer class."""
    
    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection to RabbitMQ."""
        consumer = EmailConsumer()
        
        with patch('app.consumers.email_consumer.connect_robust') as mock_connect:
            # Mock connection and channel
            mock_connection = AsyncMock()
            mock_channel = AsyncMock()
            mock_queue = AsyncMock()
            
            mock_connection.channel.return_value = mock_channel
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_queue.return_value = mock_queue
            mock_connect.return_value = mock_connection
            
            # Connect
            await consumer.connect()
            
            # Verify connection established
            assert consumer.connection is not None
            assert consumer.channel is not None
            assert consumer.queue is not None
            
            # Verify QoS was set
            mock_channel.set_qos.assert_called_once()
            
            # Verify queue was declared
            mock_channel.declare_queue.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure handling."""
        consumer = EmailConsumer()
        
        with patch('app.consumers.email_consumer.connect_robust') as mock_connect, \
             patch('app.consumers.email_consumer.logger') as mock_logger:
            
            # Mock connection failure
            mock_connect.side_effect = Exception("Connection refused")
            
            # Attempt connection - should raise
            with pytest.raises(Exception, match="Connection refused"):
                await consumer.connect()
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_success(self):
        """Test successful disconnection."""
        consumer = EmailConsumer()
        
        # Set up mock connection
        mock_connection = AsyncMock()
        consumer.connection = mock_connection
        
        # Disconnect
        await consumer.disconnect()
        
        # Verify connection was closed
        mock_connection.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_with_error(self):
        """Test disconnection handles errors gracefully."""
        consumer = EmailConsumer()
        
        # Set up mock connection that fails on close
        mock_connection = AsyncMock()
        mock_connection.close.side_effect = Exception("Close error")
        consumer.connection = mock_connection
        
        with patch('app.consumers.email_consumer.logger') as mock_logger:
            # Disconnect - should not raise
            await consumer.disconnect()
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_no_connection(self):
        """Test disconnect when no connection exists."""
        consumer = EmailConsumer()
        consumer.connection = None
        
        # Should not raise
        await consumer.disconnect()
    
    @pytest.mark.asyncio
    async def test_process_message_success(self):
        """Test successful message processing."""
        consumer = EmailConsumer()
        
        # Create test message
        queue_msg_data = {
            "notification_id": str(uuid4()),
            "user_id": str(uuid4()),
            "template_id": str(uuid4()),
            "variables": {"name": "Test User"},
            "priority": 0,
            "request_id": "req-123",
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {}
        }
        
        # Mock RabbitMQ message
        mock_message = AsyncMock()
        mock_message.body = json.dumps(queue_msg_data).encode()
        
        # Create proper async context manager mock for message.process()
        class MockProcessContext:
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        
        mock_message.process = Mock(return_value=MockProcessContext())
        
        with patch.object(consumer, '_handle_email', return_value=True) as mock_handle:
            # Process message
            await consumer._process_message(mock_message)
            
            # Verify email handler was called
            mock_handle.assert_called_once()
            
            # Verify message data
            call_args = mock_handle.call_args[0][0]
            assert isinstance(call_args, QueueMessage)
            assert call_args.request_id == "req-123"
    
    @pytest.mark.asyncio
    async def test_process_message_invalid_json(self):
        """Test processing message with invalid JSON."""
        consumer = EmailConsumer()
        
        # Mock message with invalid JSON
        mock_message = AsyncMock()
        mock_message.body = b"invalid json {{"
        
        # Create async context manager mock
        class MockProcessContext:
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        
        mock_message.process = Mock(return_value=MockProcessContext())
        
        with patch('app.consumers.email_consumer.logger') as mock_logger:
            # Process message - should not raise
            await consumer._process_message(mock_message)
            
            # Verify error was logged
            assert any("Invalid JSON" in str(call) for call in mock_logger.error.call_args_list)
    
    @pytest.mark.asyncio
    async def test_process_message_validation_error(self):
        """Test processing message with validation error."""
        consumer = EmailConsumer()
        
        # Create invalid message data (missing required fields)
        invalid_data = {
            "notification_id": str(uuid4()),
            # Missing required fields
        }
        
        mock_message = AsyncMock()
        mock_message.body = json.dumps(invalid_data).encode()
        
        # Create async context manager mock
        class MockProcessContext:
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        
        mock_message.process = Mock(return_value=MockProcessContext())
        
        with patch('app.consumers.email_consumer.logger') as mock_logger:
            # Process message - should raise due to validation error
            with pytest.raises(Exception):
                await consumer._process_message(mock_message)
    
    @pytest.mark.asyncio
    async def test_process_message_processing_failure(self):
        """Test handling email processing failure."""
        consumer = EmailConsumer()
        
        queue_msg_data = {
            "notification_id": str(uuid4()),
            "user_id": str(uuid4()),
            "template_id": str(uuid4()),
            "variables": {"name": "Test User"},
            "priority": 0,
            "request_id": "req-123",
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {}
        }
        
        mock_message = AsyncMock()
        mock_message.body = json.dumps(queue_msg_data).encode()
        
        # Create async context manager mock
        class MockProcessContext:
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        
        mock_message.process = Mock(return_value=MockProcessContext())
        
        with patch.object(consumer, '_handle_email', return_value=False) as mock_handle:
            # Process message - should raise when processing fails
            with pytest.raises(Exception, match="Email processing failed"):
                await consumer._process_message(mock_message)
    
    @pytest.mark.asyncio
    async def test_handle_email_success(self):
        """Test successful email handling."""
        consumer = EmailConsumer()
        
        queue_msg = QueueMessage(
            notification_id=uuid4(),
            user_id=uuid4(),
            template_id=uuid4(),
            variables={"name": "Test User"},
            priority=0,
            request_id="req-123",
            created_at=datetime.utcnow(),
            metadata={}
        )
        
        with patch('app.consumers.email_consumer.get_db_session') as mock_session_ctx, \
             patch('app.consumers.email_consumer.EmailDeliveryRepository') as mock_repo, \
             patch('app.consumers.email_consumer.ExternalAPIClient') as mock_api, \
             patch('app.consumers.email_consumer.EmailService') as mock_service_class:
            
            # Mock database session context manager
            mock_session = AsyncMock()
            mock_session_cm = AsyncMock()
            mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session_ctx.return_value = mock_session_cm
            
            # Mock email service
            mock_service = AsyncMock()
            mock_service.process_email_notification.return_value = True
            mock_service_class.return_value = mock_service
            
            # Handle email
            result = await consumer._handle_email(queue_msg)
            
            # Verify result
            assert result is True
            
            # Verify service was created and called
            mock_service.process_email_notification.assert_called_once_with(queue_msg)
    
    @pytest.mark.asyncio
    async def test_handle_email_failure(self):
        """Test email handling failure."""
        consumer = EmailConsumer()
        
        queue_msg = QueueMessage(
            notification_id=uuid4(),
            user_id=uuid4(),
            template_id=uuid4(),
            variables={"name": "Test User"},
            priority=0,
            request_id="req-123",
            created_at=datetime.utcnow(),
            metadata={}
        )
        
        with patch('app.consumers.email_consumer.get_db_session') as mock_session_ctx, \
             patch('app.consumers.email_consumer.EmailDeliveryRepository') as mock_repo, \
             patch('app.consumers.email_consumer.ExternalAPIClient') as mock_api, \
             patch('app.consumers.email_consumer.EmailService') as mock_service_class:
            
            # Mock database session context manager
            mock_session = AsyncMock()
            mock_session_cm = AsyncMock()
            mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session_ctx.return_value = mock_session_cm
            
            # Mock email service to return False
            mock_service = AsyncMock()
            mock_service.process_email_notification.return_value = False
            mock_service_class.return_value = mock_service
            
            # Handle email
            result = await consumer._handle_email(queue_msg)
            
            # Verify result
            assert result is False
    
    @pytest.mark.asyncio
    async def test_start_consuming_initialization(self):
        """Test start_consuming initializes properly."""
        consumer = EmailConsumer()
        
        with patch('app.consumers.email_consumer.cache') as mock_cache, \
             patch.object(consumer, 'connect') as mock_connect, \
             patch.object(consumer, 'disconnect') as mock_disconnect:
            
            mock_cache.connect = AsyncMock()
            mock_cache.disconnect = AsyncMock()
            
            # Mock queue
            consumer.queue = AsyncMock()
            consumer.queue.consume = AsyncMock()
            
            # Create a task that will be cancelled
            import asyncio
            task = asyncio.create_task(consumer.start_consuming())
            
            # Give it a moment to start
            await asyncio.sleep(0.1)
            
            # Cancel the task
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Verify cache connection was attempted
            mock_cache.connect.assert_called_once()
            
            # Verify RabbitMQ connection was attempted
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_consumer_queue_declaration_with_dlq(self):
        """Test queue is declared with DLQ configuration."""
        consumer = EmailConsumer()
        
        with patch('app.consumers.email_consumer.connect_robust') as mock_connect:
            mock_connection = AsyncMock()
            mock_channel = AsyncMock()
            mock_queue = AsyncMock()
            
            mock_connection.channel.return_value = mock_channel
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_queue.return_value = mock_queue
            mock_connect.return_value = mock_connection
            
            await consumer.connect()
            
            # Verify queue was declared with DLQ arguments
            mock_channel.declare_queue.assert_called_once()
            call_args = mock_channel.declare_queue.call_args
            
            # Check queue name and durability
            assert call_args[0][0] == "email.queue"
            assert call_args[1]["durable"] is True
            
            # Check DLQ configuration
            assert "arguments" in call_args[1]
            assert "x-dead-letter-exchange" in call_args[1]["arguments"]
            assert "x-dead-letter-routing-key" in call_args[1]["arguments"]
    
    @pytest.mark.asyncio
    async def test_consumer_prefetch_count_set(self):
        """Test QoS prefetch count is configured."""
        consumer = EmailConsumer()
        
        with patch('app.consumers.email_consumer.connect_robust') as mock_connect:
            mock_connection = AsyncMock()
            mock_channel = AsyncMock()
            mock_queue = AsyncMock()
            
            mock_connection.channel.return_value = mock_channel
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_queue.return_value = mock_queue
            mock_connect.return_value = mock_connection
            
            await consumer.connect()
            
            # Verify QoS was configured
            mock_channel.set_qos.assert_called_once()
            call_args = mock_channel.set_qos.call_args
            
            # Check prefetch count was set
            assert "prefetch_count" in call_args[1]
    
    @pytest.mark.asyncio
    async def test_process_message_logs_notification_info(self):
        """Test that message processing logs notification details."""
        consumer = EmailConsumer()
        
        notification_id = uuid4()
        user_id = uuid4()
        
        queue_msg_data = {
            "notification_id": str(notification_id),
            "user_id": str(user_id),
            "template_id": str(uuid4()),
            "variables": {"name": "Test User"},
            "priority": 0,
            "request_id": "req-123",
            "created_at": datetime.utcnow().isoformat(),
            "metadata": {}
        }
        
        mock_message = AsyncMock()
        mock_message.body = json.dumps(queue_msg_data).encode()
        
        # Create async context manager mock
        class MockProcessContext:
            async def __aenter__(self):
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None
        
        mock_message.process = Mock(return_value=MockProcessContext())
        
        with patch.object(consumer, '_handle_email', return_value=True), \
             patch('app.consumers.email_consumer.logger') as mock_logger:
            
            await consumer._process_message(mock_message)
            
            # Verify notification details were logged
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any(str(notification_id) in call for call in info_calls)
            assert any(str(user_id) in call for call in info_calls)


class TestStartConsumer:
    """Unit tests for start_consumer function."""
    
    @pytest.mark.asyncio
    async def test_start_consumer_creates_instance(self):
        """Test start_consumer creates EmailConsumer instance."""
        with patch('app.consumers.email_consumer.EmailConsumer') as mock_class:
            mock_instance = AsyncMock()
            mock_instance.start_consuming = AsyncMock()
            mock_class.return_value = mock_instance
            
            # Create task
            import asyncio
            task = asyncio.create_task(start_consumer())
            
            # Give it a moment
            await asyncio.sleep(0.1)
            
            # Cancel
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Verify instance was created
            mock_class.assert_called_once()
            mock_instance.start_consuming.assert_called_once()
