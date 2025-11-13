"""
Test Push Service API Endpoints
Tests health check and push notification functionality
"""
import asyncio
import httpx
import json

BASE_URL = "http://127.0.0.1:8005"


async def test_health_check():
    """Test the health check endpoint"""
    print("\n" + "="*60)
    print("Testing Health Check Endpoint")
    print("="*60)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/api/v1/health")
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Service Status: {data.get('status')}")
                print(f"   Version: {data.get('version')}")
                print(f"   Timestamp: {data.get('timestamp')}")
                print("\n   Dependencies:")
                for dep, status in data.get('dependencies', {}).items():
                    icon = "✅" if status == "healthy" else "❌"
                    print(f"   {icon} {dep}: {status}")
                return True
            else:
                print(f"❌ Health check failed with status {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Health check failed: {str(e)}")
        return False


async def test_send_push_notification():
    """Test sending a push notification via API"""
    print("\n" + "="*60)
    print("Testing Send Push Notification Endpoint")
    print("="*60)
    
    # Sample push notification payload
    payload = {
        "user_id": "test-user-123",
        "title": "Test Push Notification",
        "body": "This is a test push notification from the push-service API",
        "data": {
            "notification_type": "test",
            "action": "open_app",
            "timestamp": "2025-11-13T06:30:00Z"
        },
        "priority": "high",
        "badge": 1
    }
    
    print(f"\nPayload:")
    print(json.dumps(payload, indent=2))
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/v1/push/send",
                json=payload,
                timeout=30.0
            )
            
            print(f"\nStatus Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ Push notification queued successfully")
                print(f"   Message ID: {data.get('message_id')}")
                print(f"   Status: {data.get('status')}")
                return True
            else:
                print(f"❌ Failed to send push notification")
                return False
                
    except Exception as e:
        print(f"❌ Send push failed: {str(e)}")
        return False


async def test_send_push_via_rabbitmq():
    """Test sending a push notification via RabbitMQ"""
    print("\n" + "="*60)
    print("Testing Send Push via RabbitMQ")
    print("="*60)
    
    try:
        import aio_pika
        
        # Sample notification message
        message = {
            "user_id": "test-user-456",
            "title": "RabbitMQ Test Notification",
            "body": "This notification was sent directly via RabbitMQ",
            "data": {
                "source": "rabbitmq",
                "test": True
            }
        }
        
        print(f"\nMessage:")
        print(json.dumps(message, indent=2))
        
        # Connect to RabbitMQ
        connection = await aio_pika.connect_robust(
            "amqp://guest:guest@localhost:5672/"
        )
        
        async with connection:
            channel = await connection.channel()
            
            # Publish message to push queue
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode(),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key="push.queue"
            )
            
            print("\n✅ Message published to RabbitMQ successfully")
            print("   Queue: push.queue")
            print("   Check push-service logs for processing")
            return True
            
    except Exception as e:
        print(f"❌ RabbitMQ publish failed: {str(e)}")
        return False


async def test_get_delivery_status():
    """Test getting delivery status for a notification"""
    print("\n" + "="*60)
    print("Testing Get Delivery Status Endpoint")
    print("="*60)
    
    # First send a notification to get an ID
    print("\nSending test notification first...")
    
    payload = {
        "user_id": "test-user-789",
        "title": "Status Test",
        "body": "Testing delivery status tracking"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Send notification
            send_response = await client.post(
                f"{BASE_URL}/api/v1/push/send",
                json=payload,
                timeout=30.0
            )
            
            if send_response.status_code != 200:
                print("❌ Failed to send test notification")
                return False
            
            message_id = send_response.json().get('message_id')
            print(f"✅ Notification sent with ID: {message_id}")
            
            # Wait a moment for processing
            await asyncio.sleep(2)
            
            # Get status
            print(f"\nGetting status for message: {message_id}")
            status_response = await client.get(
                f"{BASE_URL}/api/v1/push/status/{message_id}"
            )
            
            print(f"Status Code: {status_response.status_code}")
            print(f"Response: {json.dumps(status_response.json(), indent=2)}")
            
            if status_response.status_code == 200:
                data = status_response.json()
                print(f"\n✅ Retrieved delivery status")
                print(f"   Message ID: {data.get('message_id')}")
                print(f"   Status: {data.get('status')}")
                print(f"   Sent At: {data.get('sent_at')}")
                return True
            else:
                print(f"⚠️  Status endpoint returned {status_response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Status check failed: {str(e)}")
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("PUSH SERVICE API TESTS")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    
    results = {}
    
    # Test 1: Health Check
    results["Health Check"] = await test_health_check()
    
    # Test 2: Send Push Notification
    results["Send Push (API)"] = await test_send_push_notification()
    
    # Test 3: Send via RabbitMQ
    results["Send Push (RabbitMQ)"] = await test_send_push_via_rabbitmq()
    
    # Test 4: Get Delivery Status
    results["Get Delivery Status"] = await test_get_delivery_status()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:30} {status}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
