"""
RabbitMQ Email Queue Consumer

Consumes messages from the email.queue and processes email notifications.
Implements proper message acknowledgment and error handling with DLQ support.
"""

import json
import asyncio
from typing import Optional
import aio_pika
from aio_pika import connect_robust, IncomingMessage
from aio_pika.abc import AbstractRobustConnection

from app.config import settings
from app.schemas.email import QueueMessage
from app.services.email_service import EmailService
from app.services.external_api import ExternalAPIClient
from app.db.repositories.email_delivery_repository import EmailDeliveryRepository
from app.db.session import get_db_session
from app.utils.logger import get_logger
from app.utils.cache import cache

logger = get_logger(__name__)


class EmailConsumer:
    """
    Consumer for email notification queue.
    
    Processes messages from RabbitMQ with:
    - Automatic reconnection on connection loss
    - Message acknowledgment
    - Dead-letter queue for failed messages
    - Concurrent message processing
    """
    
    def __init__(self):
        self.connection: Optional[AbstractRobustConnection] = None
        self.channel = None
        self.queue = None
    
    async def connect(self):
        """Connect to RabbitMQ with automatic reconnection."""
        try:
            logger.info(f"Connecting to RabbitMQ: {settings.RABBITMQ_URL}")
            
            self.connection = await connect_robust(
                settings.RABBITMQ_URL,
                heartbeat=60,
                connection_attempts=5,
                retry_delay=5
            )
            
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=settings.RABBITMQ_PREFETCH_COUNT)
            
            # Declare the email queue
            self.queue = await self.channel.declare_queue(
                settings.RABBITMQ_EMAIL_QUEUE,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": "",
                    "x-dead-letter-routing-key": settings.RABBITMQ_DLQ
                }
            )
            
            logger.info(f"Connected to RabbitMQ and listening on queue: {settings.RABBITMQ_EMAIL_QUEUE}")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise
    
    async def disconnect(self):
        """Disconnect from RabbitMQ."""
        try:
            if self.connection:
                await self.connection.close()
                logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {str(e)}")
    
    async def start_consuming(self):
        """Start consuming messages from the queue."""
        try:
            # Connect to Redis cache
            await cache.connect()
            
            # Connect to RabbitMQ
            await self.connect()
            
            # Start consuming
            logger.info("Starting to consume messages...")
            await self.queue.consume(self._process_message)
            
            # Keep running
            logger.info("Email consumer is running. Press Ctrl+C to stop.")
            await asyncio.Future()  # Run forever
            
        except asyncio.CancelledError:
            logger.info("Consumer task cancelled")
            await self.disconnect()
            await cache.disconnect()
        except Exception as e:
            logger.error(f"Error in consumer: {str(e)}")
            await self.disconnect()
            await cache.disconnect()
            raise
    
    async def _process_message(self, message: IncomingMessage):
        """
        Process a single message from the queue.
        
        Implements proper error handling and message acknowledgment.
        """
        async with message.process():
            try:
                # Parse message
                body = json.loads(message.body.decode())
                queue_msg = QueueMessage(**body)
                
                logger.info(
                    f"Received message for notification: {queue_msg.notification_id} "
                    f"(user: {queue_msg.user_id})"
                )
                
                # Process email
                success = await self._handle_email(queue_msg)
                
                if success:
                    logger.info(f"Successfully processed notification: {queue_msg.notification_id}")
                    # Message will be auto-acknowledged by context manager
                else:
                    logger.error(f"Failed to process notification: {queue_msg.notification_id}")
                    # Reject and requeue for retry
                    # After max retries, message goes to DLQ
                    raise Exception("Email processing failed")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in message: {str(e)}")
                # Don't requeue invalid messages
                # Message will be auto-acknowledged and lost
                
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                # Re-raise to trigger message requeue or DLQ
                raise
    
    async def _handle_email(self, queue_msg: QueueMessage) -> bool:
        """
        Handle email processing with database session.
        
        Creates new database session for each message to ensure isolation.
        """
        async with get_db_session() as session:
            # Create dependencies
            repository = EmailDeliveryRepository(session)
            api_client = ExternalAPIClient()
            email_service = EmailService(repository, api_client)
            
            # Process the email
            return await email_service.process_email_notification(queue_msg)


async def start_consumer():
    """
    Entry point for starting the email consumer.
    
    Called from main.py on application startup.
    """
    consumer = EmailConsumer()
    await consumer.start_consuming()
