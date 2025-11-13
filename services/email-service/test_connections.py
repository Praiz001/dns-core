"""
Email Service Connection Tests

Tests database, RabbitMQ, and Redis connections.
"""

import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import aio_pika
import redis.asyncio as redis

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def test_database():
    """Test PostgreSQL database connection."""
    print("\n" + "=" * 60)
    print("Testing Database Connection")
    print("=" * 60)
    
    try:
        # Create engine with pgbouncer compatibility
        engine = create_async_engine(
            str(settings.DATABASE_URL),
            echo=False,
            connect_args={
                "prepared_statement_cache_size": 0,  # Required for pgbouncer
                "statement_cache_size": 0
            }
        )
        
        # Test connection
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            await conn.commit()
            
        print(f"Database URL: {str(settings.DATABASE_URL).split('@')[1]}")
        print("Status: ✅ CONNECTED")
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"Status: ❌ FAILED")
        print(f"Error: {str(e)}")
        return False


async def test_rabbitmq():
    """Test RabbitMQ connection."""
    print("\n" + "=" * 60)
    print("Testing RabbitMQ Connection")
    print("=" * 60)
    
    try:
        # Connect to RabbitMQ
        connection = await aio_pika.connect_robust(
            settings.RABBITMQ_URL,
            heartbeat=60,
            connection_attempts=3,
            retry_delay=2
        )
        
        # Create channel
        channel = await connection.channel()
        
        # Declare queue
        queue = await channel.declare_queue(
            settings.RABBITMQ_EMAIL_QUEUE,
            durable=True
        )
        
        print(f"RabbitMQ URL: {settings.RABBITMQ_URL}")
        print(f"Queue: {settings.RABBITMQ_EMAIL_QUEUE}")
        print(f"Queue Messages: {queue.declaration_result.message_count}")
        print("Status: ✅ CONNECTED")
        
        await connection.close()
        return True
        
    except Exception as e:
        print(f"Status: ❌ FAILED")
        print(f"Error: {str(e)}")
        return False


async def test_redis():
    """Test Redis connection."""
    print("\n" + "=" * 60)
    print("Testing Redis Connection")
    print("=" * 60)
    
    try:
        # Connect to Redis
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        
        # Test connection
        await redis_client.ping()
        
        # Test set/get
        test_key = "email_service:test"
        await redis_client.set(test_key, "test_value", ex=10)
        value = await redis_client.get(test_key)
        
        print(f"Redis URL: {settings.REDIS_URL}")
        print(f"Test Key: {test_key} = {value}")
        print("Status: ✅ CONNECTED")
        
        await redis_client.close()
        return True
        
    except Exception as e:
        print(f"Status: ❌ FAILED")
        print(f"Error: {str(e)}")
        return False


async def test_smtp():
    """Test SMTP configuration."""
    print("\n" + "=" * 60)
    print("Testing SMTP Configuration")
    print("=" * 60)
    
    try:
        if settings.EMAIL_PROVIDER == "smtp":
            print(f"Provider: SMTP")
            print(f"Host: {settings.SMTP_HOST}")
            print(f"Port: {settings.SMTP_PORT}")
            print(f"Username: {settings.SMTP_USERNAME}")
            print(f"TLS: {settings.SMTP_USE_TLS}")
            print(f"From: {settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>")
            
            # Check if credentials are set
            if settings.SMTP_HOST and settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                print("Status: ✅ CONFIGURED")
                return True
            else:
                print("Status: ⚠️  INCOMPLETE - Missing credentials")
                return False
        else:
            print(f"Provider: {settings.EMAIL_PROVIDER}")
            print("Status: ⚠️  SMTP not active")
            return True
            
    except Exception as e:
        print(f"Status: ❌ FAILED")
        print(f"Error: {str(e)}")
        return False


async def main():
    """Run all connection tests."""
    print("\n" + "=" * 60)
    print("EMAIL SERVICE CONNECTION TESTS")
    print("=" * 60)
    
    results = {
        "Database": await test_database(),
        "RabbitMQ": await test_rabbitmq(),
        "Redis": await test_redis(),
        "SMTP": await test_smtp(),
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for service, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {service}: {'PASSED' if status else 'FAILED'}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All connection tests passed!")
        print("=" * 60)
        return 0
    else:
        print("❌ Some connection tests failed!")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
