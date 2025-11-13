"""
Test connections to all external services
Run this to verify database, RabbitMQ, and Redis connectivity
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import aio_pika
import redis.asyncio as aioredis
from app.config import settings


async def test_database():
    """Test PostgreSQL/Supabase database connection"""
    print("\n" + "="*60)
    print("Testing Database Connection (Async)")
    print("="*60)
    print(f"DATABASE_URL: {settings.DATABASE_URL}")
    
    # First try raw asyncpg connection
    print("\n--- Testing Raw asyncpg Connection ---")
    try:
        import asyncpg
        from urllib.parse import urlparse
        
        # Parse the database URL
        parsed = urlparse(settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://'))
        
        # Create direct asyncpg connection with statement_cache_size=0
        conn = await asyncpg.connect(
            host=parsed.hostname,
            port=parsed.port,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/'),
            statement_cache_size=0,  # Disable prepared statements
            server_settings={'application_name': 'push-service-test'}
        )
        
        version = await conn.fetchval('SELECT version()')
        print("✅ Raw asyncpg connection: SUCCESS")
        print(f"   PostgreSQL version: {version}")
        
        test_value = await conn.fetchval('SELECT 1 as test')
        print(f"   Test query result: {test_value}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Raw asyncpg connection: FAILED")
        print(f"   Error: {type(e).__name__}: {str(e)}")
        return False
    
    # Now try with SQLAlchemy
    print("\n--- Testing SQLAlchemy AsyncEngine ---")
    try:
        # Create async engine with pgbouncer compatibility
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            connect_args={
                "statement_cache_size": 0,  # Disable prepared statements for pgbouncer
                "server_settings": {
                    "application_name": "push-service-test"
                }
            }
        )
        
        # Test connection
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            version = result.scalar()
            print("✅ Database connection: SUCCESS")
            print(f"   PostgreSQL version: {version}")
            
            # Test a simple query
            result = await conn.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            print(f"   Test query result: {test_value}")
            
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Database connection: FAILED")
        print(f"   Error: {type(e).__name__}: {str(e)}")
        return False


async def test_rabbitmq():
    """Test RabbitMQ connection"""
    print("\n" + "="*60)
    print("Testing RabbitMQ Connection (Async)")
    print("="*60)
    print(f"RABBITMQ_URL: {settings.RABBITMQ_URL}")
    
    try:
        # Connect to RabbitMQ
        connection = await aio_pika.connect_robust(
            settings.RABBITMQ_URL,
            timeout=10
        )
        
        print("✅ RabbitMQ connection: SUCCESS")
        
        # Create a channel
        channel = await connection.channel()
        print("   Channel created successfully")
        
        # Declare a test queue
        queue = await channel.declare_queue(
            "test_connection_queue",
            auto_delete=True
        )
        print(f"   Test queue declared: {queue.name}")
        
        # Clean up
        await queue.delete()
        await channel.close()
        await connection.close()
        
        print("   Connection closed successfully")
        return True
        
    except Exception as e:
        print(f"❌ RabbitMQ connection: FAILED")
        print(f"   Error: {type(e).__name__}: {str(e)}")
        return False


async def test_redis():
    """Test Redis connection"""
    print("\n" + "="*60)
    print("Testing Redis Connection (Async)")
    print("="*60)
    print(f"REDIS_URL: {settings.REDIS_URL}")
    
    try:
        # Connect to Redis
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        
        # Test ping
        pong = await redis_client.ping()
        print("✅ Redis connection: SUCCESS")
        print(f"   PING response: {pong}")
        
        # Test set/get
        test_key = "test_connection_key"
        test_value = "Hello from push-service!"
        
        await redis_client.set(test_key, test_value, ex=10)
        retrieved_value = await redis_client.get(test_key)
        
        print(f"   SET test: {test_key} = {test_value}")
        print(f"   GET test: {retrieved_value}")
        
        # Clean up
        await redis_client.delete(test_key)
        await redis_client.close()
        
        print("   Connection closed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Redis connection: FAILED")
        print(f"   Error: {type(e).__name__}: {str(e)}")
        return False


async def main():
    """Run all connection tests"""
    print("\n" + "="*60)
    print("PUSH SERVICE - CONNECTION TESTS")
    print("="*60)
    
    results = {
        "Database": await test_database(),
        "RabbitMQ": await test_rabbitmq(),
        "Redis": await test_redis(),
    }
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_passed = True
    for service, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{service:15} {status}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n🎉 All services are connected successfully!")
        return 0
    else:
        print("\n⚠️  Some services failed to connect. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
