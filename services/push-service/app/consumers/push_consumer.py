"""RabbitMQ Consumer for Push Notifications"""
import json
import asyncio
import aio_pika
from typing import Dict, Any
from pydantic import ValidationError

from app.config import settings
from app.services.push_service import PushService
from app.schemas.push import NotificationMessage
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PushConsumer:
    """Consumer for push notification queue"""
    
    def __init__(self, push_service: PushService):
        self.push_service = push_service
        self.connection = None
        self.channel = None
    
    async def connect(self):
        """Connect to RabbitMQ"""
        try:
            self.connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URL,
                timeout=10
            )
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=settings.RABBITMQ_PREFETCH_COUNT)
            logger.info("Connected to RabbitMQ successfully")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise
    
    async def disconnect(self):
        """Disconnect from RabbitMQ"""
        try:
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
                logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {str(e)}")
    
    async def start_consuming(self):
        """Start consuming messages from push queue"""
        if not self.channel:
            await self.connect()
        
        try:
            # Declare queue with DLQ configuration
            queue = await self.channel.declare_queue(
                settings.RABBITMQ_QUEUE,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": settings.RABBITMQ_DLX_EXCHANGE,
                    "x-dead-letter-routing-key": settings.RABBITMQ_DLX_ROUTING_KEY
                }
            )
            
            logger.info(f"Started consuming from {settings.RABBITMQ_QUEUE}")
            
            # Start consuming
            await queue.consume(self.process_message)
            
            # Keep running
            await asyncio.Future()
            
        except Exception as e:
            logger.error(f"Error in consumer: {str(e)}")
            raise
    
    async def process_message(self, message: aio_pika.IncomingMessage):
        """Process a single message from the queue"""
        async with message.process():
            try:
                # Parse message body
                data = json.loads(message.body.decode())
                logger.info(f"Received notification {data.get('notification_id')} for user {data.get('user_id')}")
                
                # Validate message schema
                try:
                    notification = NotificationMessage(**data)
                except ValidationError as e:
                    logger.error(f"Invalid message format: {str(e)}")
                    # Message will be rejected and sent to DLQ
                    raise
                
                # Process notification
                await self.push_service.process_notification(data)
                
                # Message will be auto-acknowledged on successful processing
                logger.info(f"Successfully processed notification {data.get('notification_id')}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode message: {str(e)}")
                # Reject message - invalid JSON
                raise
            
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                # Message will be rejected and sent to DLQ
                raise


async def start_consumer():
    """Entry point for starting the consumer"""
    from app.api.dependencies import get_push_service
    
    logger.info("Initializing push consumer...")
    
    push_service = get_push_service()
    consumer = PushConsumer(push_service)
    
    try:
        await consumer.start_consuming()
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
    except Exception as e:
        logger.error(f"Consumer error: {str(e)}")
        raise
    finally:
        await consumer.disconnect()
