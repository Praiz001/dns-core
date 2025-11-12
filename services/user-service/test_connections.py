"""
Test script to verify Redis and RabbitMQ connections
Run this with: python test_connections.py
"""

import json
import os
import sys

import django
import pika

# Setup Django
os.environ["DJANGO_SETTINGS_MODULE"] = "user_service.settings"
django.setup()

from django.conf import settings  # noqa: E402
from django.core.cache import cache  # noqa: E402


def test_redis():
    """Test Redis connection"""
    print("\n=== Testing Redis Connection ===")
    try:
        # Try to set and get a value
        test_key = "test_connection"
        test_value = "Hello from Upstash Redis!"

        cache.set(test_key, test_value, 60)
        retrieved = cache.get(test_key)

        if retrieved == test_value:
            print("✅ Redis connection successful!")
            print(f"   Set and retrieved: {retrieved}")
            cache.delete(test_key)
            return True
        else:
            print("❌ Redis connection failed - value mismatch")
            return False

    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False


def test_rabbitmq():
    """Test RabbitMQ connection"""
    print("\n=== Testing RabbitMQ Connection ===")
    try:
        import ssl

        config = settings.RABBITMQ_CONFIG

        # Setup credentials
        credentials = pika.PlainCredentials(config["USER"], config["PASSWORD"])

        # Setup SSL context if needed
        ssl_options = None
        if config.get("USE_SSL"):
            ssl_context = ssl.create_default_context()
            ssl_options = pika.SSLOptions(ssl_context)

        # Setup connection parameters with SSL if needed
        parameters = pika.ConnectionParameters(
            host=config["HOST"],
            port=config["PORT"],
            virtual_host=config["VHOST"],
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
            ssl_options=ssl_options,
        )

        # Connect
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Declare a test queue
        test_queue = "test_queue"
        channel.queue_declare(queue=test_queue, durable=False)

        # Publish a test message
        test_message = {"test": "Hello from CloudAMQP!", "timestamp": str(django.utils.timezone.now())}

        channel.basic_publish(exchange="", routing_key=test_queue, body=json.dumps(test_message))

        print("✅ RabbitMQ connection successful!")
        print(f"   Published test message to queue: {test_queue}")

        # Consume the test message
        method_frame, header_frame, body = channel.basic_get(test_queue)

        if method_frame:
            received = json.loads(body)
            print(f"   Received test message: {received['test']}")
            channel.basic_ack(method_frame.delivery_tag)

        # Clean up
        channel.queue_delete(test_queue)
        connection.close()

        return True

    except Exception as e:
        print(f"❌ RabbitMQ connection failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing cloud service connections...")
    print(f"Redis: {settings.CACHES['default']['LOCATION']}")
    print(f"RabbitMQ: {settings.RABBITMQ_CONFIG['HOST']}")

    redis_ok = test_redis()
    rabbitmq_ok = test_rabbitmq()

    print("\n=== Summary ===")
    print(f"Redis: {'✅ Connected' if redis_ok else '❌ Failed'}")
    print(f"RabbitMQ: {'✅ Connected' if rabbitmq_ok else '❌ Failed'}")

    if redis_ok and rabbitmq_ok:
        print("\n🎉 All connections successful! You're ready to go!")
        sys.exit(0)
    else:
        print("\n⚠️  Some connections failed. Check the errors above.")
        sys.exit(1)
