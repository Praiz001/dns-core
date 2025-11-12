"""
RabbitMQ consumer for handling notification requests
"""
import json
import pika
import logging
import time
from django.conf import settings
from django.core.cache import cache
from pybreaker import CircuitBreaker, CircuitBreakerError
from .models import User
from .serializers import UserPreferenceSerializer

logger = logging.getLogger(__name__)

# Circuit breaker for RabbitMQ connection
rabbitmq_breaker = CircuitBreaker(
    fail_max=5,
    timeout_duration=60,
    name='RabbitMQ Connection'
)


class RabbitMQConsumer:
    """RabbitMQ consumer for push notification queue"""
    
    def __init__(self):
        self.config = settings.RABBITMQ_CONFIG
        self.connection = None
        self.channel = None
        self.retry_count = 0
        self.max_retries = 3
    
    @rabbitmq_breaker
    def connect(self):
        """Establish connection to RabbitMQ"""
        import ssl
        
        credentials = pika.PlainCredentials(
            self.config['USER'],
            self.config['PASSWORD']
        )
        
        # Setup SSL context if needed
        ssl_options = None
        if self.config.get('USE_SSL'):
            ssl_context = ssl.create_default_context()
            ssl_options = pika.SSLOptions(ssl_context)
        
        parameters = pika.ConnectionParameters(
            host=self.config['HOST'],
            port=self.config['PORT'],
            virtual_host=self.config['VHOST'],
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
            ssl_options=ssl_options,
        )
        
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        
        # Declare queue with durability
        self.channel.queue_declare(
            queue=self.config['QUEUE_PUSH'],
            durable=True
        )
        
        logger.info("Connected to RabbitMQ successfully")
    
    def get_user_preferences(self, user_id):
        """
        Get user preferences with caching
        Returns user data including preferences
        """
        cache_key = f"user_preferences:{user_id}"
        
        # Try cache first
        cached_prefs = cache.get(cache_key)
        if cached_prefs:
            logger.debug(f"Retrieved preferences from cache for user: {user_id}")
            return cached_prefs
        
        # Fetch from database
        try:
            user = User.objects.select_related('preferences').get(id=user_id)
            
            user_data = {
                'user_id': str(user.id),
                'name': user.name,
                'email': user.email,
                'push_token': user.push_token,
                'preferences': UserPreferenceSerializer(user.preferences).data if user.preferences else None,
                'email_verified': user.email_verified,
            }
            
            # Cache for 1 hour
            cache.set(cache_key, user_data, 3600)
            
            logger.debug(f"Retrieved preferences from database for user: {user_id}")
            return user_data
        
        except User.DoesNotExist:
            logger.warning(f"User not found: {user_id}")
            return None
    
    def process_message(self, ch, method, properties, body):
        """
        Process incoming notification message
        Expected format:
        {
            "notification_type": "push",
            "user_id": "uuid",
            "template_code": "string",
            "variables": {"name": "...", "link": "..."},
            "request_id": "string",
            "priority": 1,
            "metadata": {}
        }
        """
        try:
            # Parse message
            message = json.loads(body)
            request_id = message.get('request_id', 'unknown')
            user_id = message.get('user_id')
            
            logger.info(
                f"Processing notification message",
                extra={
                    'request_id': request_id,
                    'user_id': user_id,
                    'notification_type': message.get('notification_type')
                }
            )
            
            # Get user preferences
            user_data = self.get_user_preferences(user_id)
            
            if not user_data:
                logger.error(f"User not found: {user_id}", extra={'request_id': request_id})
                # Reject message - user doesn't exist
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
            
            # Check if user has push notifications enabled
            if not user_data.get('preferences', {}).get('push', False):
                logger.info(
                    f"Push notifications disabled for user: {user_id}",
                    extra={'request_id': request_id}
                )
                # Acknowledge message - user has disabled push notifications
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Check if user has push token
            if not user_data.get('push_token'):
                logger.warning(
                    f"No push token for user: {user_id}",
                    extra={'request_id': request_id}
                )
                # Acknowledge message - can't send push without token
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Merge user data with message variables
            enhanced_message = {
                **message,
                'user_data': user_data,
                'variables': {
                    **message.get('variables', {}),
                    'name': user_data['name'],
                }
            }
            
            # TODO: Forward to push service or process here
            # For now, just log the enhanced message
            logger.info(
                f"Enhanced message prepared for push service",
                extra={
                    'request_id': request_id,
                    'user_id': user_id,
                    'has_push_token': bool(user_data.get('push_token'))
                }
            )
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            self.retry_count = 0  # Reset retry counter on success
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}", exc_info=True)
            # Reject malformed message
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            
            # Implement exponential backoff retry
            if self.retry_count < self.max_retries:
                self.retry_count += 1
                backoff_time = 2 ** self.retry_count
                logger.info(f"Retrying in {backoff_time} seconds (attempt {self.retry_count}/{self.max_retries})")
                time.sleep(backoff_time)
                
                # Requeue message
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            else:
                # Max retries exceeded, move to dead letter queue
                logger.error(f"Max retries exceeded, rejecting message")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                self.retry_count = 0
    
    def start_consuming(self):
        """Start consuming messages from queue"""
        try:
            if not self.channel:
                self.connect()
            
            # Set QoS to process one message at a time
            self.channel.basic_qos(prefetch_count=1)
            
            # Start consuming
            self.channel.basic_consume(
                queue=self.config['QUEUE_PUSH'],
                on_message_callback=self.process_message,
                auto_ack=False
            )
            
            logger.info(f"Started consuming from queue: {self.config['QUEUE_PUSH']}")
            self.channel.start_consuming()
        
        except CircuitBreakerError:
            logger.error("Circuit breaker is open, unable to connect to RabbitMQ")
            time.sleep(60)  # Wait before retrying
        
        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
            self.stop_consuming()
        
        except Exception as e:
            logger.error(f"Error in consumer: {e}", exc_info=True)
            time.sleep(5)  # Wait before retrying
    
    def stop_consuming(self):
        """Stop consuming and close connections"""
        if self.channel:
            self.channel.stop_consuming()
        
        if self.connection and not self.connection.is_closed:
            self.connection.close()
        
        logger.info("Stopped consuming from RabbitMQ")


def run_consumer():
    """Main function to run the consumer with auto-reconnect"""
    consumer = RabbitMQConsumer()
    
    logger.info("Starting RabbitMQ consumer...")
    
    while True:
        try:
            consumer.start_consuming()
        except Exception as e:
            logger.error(f"Consumer crashed: {e}", exc_info=True)
            logger.info("Restarting consumer in 10 seconds...")
            time.sleep(10)


if __name__ == '__main__':
    run_consumer()
