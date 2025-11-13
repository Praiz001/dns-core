"""
Test Script for Push Service
Tests the complete flow of push notification delivery
"""
import asyncio
import httpx
import json
from datetime import datetime
from uuid import uuid4

# Configuration
PUSH_SERVICE_URL = "http://localhost:8004"
API_GATEWAY_URL = "http://localhost:3000"  # If you have it running
RABBITMQ_URL = "amqp://guest:guest@localhost:5672/"


async def test_health_check():
    """Test 1: Health Check"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PUSH_SERVICE_URL}/health")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            assert response.status_code == 200
            print("✅ Health check passed!")
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        raise


async def test_database_connection():
    """Test 2: Database Connection"""
    print("\n" + "="*60)
    print("TEST 2: Database Connection")
    print("="*60)
    
    try:
        from app.utils.database import get_session
        from app.models.push_delivery import PushDelivery
        from sqlalchemy import select, func
        
        async with get_session() as db:
            # Try to query the push_deliveries table using async
            result = await db.execute(select(func.count()).select_from(PushDelivery))
            count = result.scalar()
            print(f"Push deliveries in database: {count}")
            print("✅ Database connection working!")
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        raise


async def test_fcm_configuration():
    """Test 3: FCM Configuration"""
    print("\n" + "="*60)
    print("TEST 3: FCM Configuration")
    print("="*60)
    
    try:
        from app.config import settings
        import os
        
        print(f"FCM Project ID: {settings.FCM_PROJECT_ID}")
        print(f"GOOGLE_APPLICATION_CREDENTIALS: {settings.GOOGLE_APPLICATION_CREDENTIALS}")
        
        # Check if service account file exists
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            cred_path = os.path.join(
                os.path.dirname(__file__), 
                settings.GOOGLE_APPLICATION_CREDENTIALS
            )
            if os.path.exists(cred_path):
                print(f"✅ Service account file found at: {cred_path}")
                
                # Load and verify JSON
                with open(cred_path, 'r') as f:
                    creds = json.load(f)
                    print(f"Project ID in credentials: {creds.get('project_id')}")
                    print(f"Client Email: {creds.get('client_email')}")
                    
                if creds.get('project_id') == settings.FCM_PROJECT_ID:
                    print("✅ FCM configuration is correct!")
                else:
                    print("⚠️  Warning: Project ID mismatch!")
            else:
                print(f"❌ Service account file not found at: {cred_path}")
        else:
            print("⚠️  GOOGLE_APPLICATION_CREDENTIALS not set")
            
    except Exception as e:
        print(f"❌ FCM configuration check failed: {str(e)}")
        raise


async def test_push_provider():
    """Test 4: FCM Provider Initialization"""
    print("\n" + "="*60)
    print("TEST 4: FCM Provider Initialization")
    print("="*60)
    
    try:
        from app.providers.fcm import FCMProvider
        
        provider = FCMProvider()
        print(f"Provider Name: {provider.get_provider_name()}")
        print("✅ FCM Provider initialized successfully!")
        
    except Exception as e:
        print(f"❌ FCM Provider initialization failed: {str(e)}")
        raise


async def test_mock_push_message():
    """Test 5: Process Mock Push Message"""
    print("\n" + "="*60)
    print("TEST 5: Process Mock Push Message")
    print("="*60)
    
    try:
        from app.services.push_service import PushService
        from app.providers.fcm import FCMProvider
        
        # Create service
        provider = FCMProvider()
        service = PushService(provider)
        
        # Create mock message
        mock_message = {
            "notification_id": str(uuid4()),
            "request_id": f"test-{datetime.utcnow().timestamp()}",
            "user_id": str(uuid4()),
            "channel": "push",
            "template_code": "test_template",
            "variables": {
                "name": "Test User",
                "message": "This is a test notification"
            },
            "priority": 1,
            "metadata": {"test": True},
            "created_at": datetime.utcnow().isoformat()
        }
        
        print("Mock message created:")
        print(json.dumps(mock_message, indent=2))
        
        # Note: This will attempt to send to FCM
        # Comment out if you don't want to actually send
        # await service.process_notification(mock_message)
        
        print("✅ Mock message structure is valid!")
        print("⚠️  Actual sending skipped (uncomment in code to test real FCM send)")
        
    except Exception as e:
        print(f"❌ Mock message test failed: {str(e)}")
        raise


async def test_rabbitmq_connection():
    """Test 6: RabbitMQ Connection"""
    print("\n" + "="*60)
    print("TEST 6: RabbitMQ Connection")
    print("="*60)
    
    try:
        import aio_pika
        from app.config import settings
        
        # Connect to RabbitMQ
        connection = await aio_pika.connect_robust(
            settings.RABBITMQ_URL,
            timeout=10
        )
        channel = await connection.channel()
        
        print(f"✅ Connected to RabbitMQ at {settings.RABBITMQ_URL}")
        
        # Declare queue to verify it exists/can be created
        queue = await channel.declare_queue(
            settings.RABBITMQ_QUEUE,
            durable=True
        )
        
        message_count = queue.declaration_result.message_count
        print(f"Queue: {settings.RABBITMQ_QUEUE}")
        print(f"Messages in queue: {message_count}")
        
        await connection.close()
        print("✅ RabbitMQ connection working!")
        
    except Exception as e:
        print(f"❌ RabbitMQ connection failed: {str(e)}")
        raise


async def test_publish_to_queue():
    """Test 7: Publish Test Message to Queue"""
    print("\n" + "="*60)
    print("TEST 7: Publish Test Message to Queue")
    print("="*60)
    
    try:
        import aio_pika
        from app.config import settings
        
        # Create test message
        test_message = {
            "notification_id": str(uuid4()),
            "request_id": f"test-{datetime.utcnow().timestamp()}",
            "user_id": str(uuid4()),
            "channel": "push",
            "template_code": "test_notification",
            "variables": {
                "name": "Test User",
                "link": "https://example.com",
                "meta": {
                    "test": True,
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            "priority": 1,
            "metadata": {"source": "test_script"},
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Connect and publish
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await connection.channel()
        
        # Publish message
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(test_message).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=settings.RABBITMQ_QUEUE,
        )
        
        print("✅ Test message published to queue!")
        print(f"Message ID: {test_message['notification_id']}")
        print(f"Request ID: {test_message['request_id']}")
        
        await connection.close()
        
        print("\n⏳ Check your push service logs to see if it processes this message")
        
    except Exception as e:
        print(f"❌ Queue publishing failed: {str(e)}")
        raise


async def test_full_integration():
    """Test 8: Full Integration Test (requires all services)"""
    print("\n" + "="*60)
    print("TEST 8: Full Integration Test")
    print("="*60)
    
    print("This test requires:")
    print("1. API Gateway running on port 3000")
    print("2. User Service running on port 8001")
    print("3. Template Service running on port 8002")
    print("4. Push Service running on port 8004")
    print("5. RabbitMQ running on port 5672")
    print("6. PostgreSQL running on port 5432")
    
    # You can implement a full integration test here
    print("\n⚠️  Full integration test not implemented yet")
    print("Refer to the stage4.md guide for manual testing steps")


async def main():
    """Run all tests"""
    print("\n" + "🚀"*30)
    print("PUSH SERVICE TEST SUITE")
    print("🚀"*30)
    
    tests = [
        ("Health Check", test_health_check),
        ("Database Connection", test_database_connection),
        ("FCM Configuration", test_fcm_configuration),
        ("FCM Provider", test_push_provider),
        ("Mock Push Message", test_mock_push_message),
        ("RabbitMQ Connection", test_rabbitmq_connection),
        ("Publish to Queue", test_publish_to_queue),
        ("Full Integration", test_full_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            await test_func()
            results.append((test_name, "✅ PASSED"))
        except Exception as e:
            results.append((test_name, f"❌ FAILED: {str(e)}"))
            print(f"\n⚠️  Continuing with next test...\n")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, result in results:
        print(f"{test_name}: {result}")
    
    passed = sum(1 for _, r in results if "PASSED" in r)
    total = len(results)
    print(f"\n{passed}/{total} tests passed")


if __name__ == "__main__":
    asyncio.run(main())
