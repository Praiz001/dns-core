"""RabbitMQ Publisher Utility"""
import json
import aio_pika
from typing import Dict, Any
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RabbitMQPublisher:
    """RabbitMQ message publisher"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        
    async def connect(self):
        """Connect to RabbitMQ"""
        if not self.connection or self.connection.is_closed:
            self.connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URL,
                timeout=10
            )
            self.channel = await self.connection.channel()
            logger.info("Connected to RabbitMQ for publishing")
    
    async def publish_notification(self, notification_data: Dict[str, Any]) -> bool:
        """
        Publish notification to RabbitMQ queue
        
        Args:
            notification_data: Notification payload
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            await self.connect()
            
            # Declare exchange
            exchange = await self.channel.declare_exchange(
                settings.RABBITMQ_EXCHANGE,
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )
            
            # Publish message
            message = aio_pika.Message(
                body=json.dumps(notification_data).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json"
            )
            
            await exchange.publish(
                message,
                routing_key=settings.RABBITMQ_ROUTING_KEY
            )
            
            logger.info(f"Published notification to RabbitMQ: {notification_data.get('notification_id')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish to RabbitMQ: {str(e)}")
            return False
    
    async def close(self):
        """Close RabbitMQ connection"""
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()
            logger.info("Closed RabbitMQ publisher connection")


# Singleton instance
_publisher = None


async def get_rabbitmq_publisher() -> RabbitMQPublisher:
    """Get or create RabbitMQ publisher instance"""
    global _publisher
    if _publisher is None:
        _publisher = RabbitMQPublisher()
    return _publisher
