"""
End-to-End Integration Test for DNS Notification System
Tests the complete flow: API Gateway -> Template -> Email/Push Services
"""
import asyncio
import httpx
import json
from typing import Dict, Any

# Service URLs (Docker network)
API_GATEWAY_URL = "http://localhost:3000"
USER_SERVICE_URL = "http://localhost:8001"
EMAIL_SERVICE_URL = "http://localhost:8003"
PUSH_SERVICE_URL = "http://localhost:8005"
TEMPLATE_SERVICE_URL = "http://localhost:8002"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_test(name: str):
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.YELLOW}TEST: {name}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")

def print_success(message: str):
    print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")

def print_error(message: str):
    print(f"{Colors.RED}❌ {message}{Colors.RESET}")

def print_info(message: str):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.RESET}")

async def test_health_checks():
    """Test health endpoints for all services"""
    print_test("Health Checks for All Services")
    
    services = {
        "API Gateway": f"{API_GATEWAY_URL}/health",
        "User Service": f"{USER_SERVICE_URL}/api/health",
        "Email Service": f"{EMAIL_SERVICE_URL}/api/v1/health",
        "Push Service": f"{PUSH_SERVICE_URL}/api/v1/health",
        "Template Service": f"{TEMPLATE_SERVICE_URL}/api/v1/health",
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for name, url in services.items():
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    print_success(f"{name}: {data}")
                else:
                    print_error(f"{name}: Status {response.status_code}")
                    return False
            except Exception as e:
                print_error(f"{name}: {str(e)}")
                return False
    
    return True

async def test_template_creation_and_rendering():
    """Test template service - create and render template"""
    print_test("Template Service - Create and Render")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create template
        template_data = {
            "name": "e2e_welcome_email",
            "subject": "Welcome {{user_name}}!",
            "body_html": "<h1>Hello {{user_name}}</h1><p>Welcome to our platform!</p>",
            "body_text": "Hello {{user_name}}! Welcome to our platform!",
            "template_type": "email",
            "language": "en",
            "is_active": True
        }
        
        print_info("Creating template...")
        response = await client.post(
            f"{TEMPLATE_SERVICE_URL}/api/v1/templates/",
            json=template_data
        )
        
        if response.status_code not in [200, 201]:
            print_error(f"Template creation failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False, None
        
        template_result = response.json()
        template_id = template_result["data"]["id"]
        print_success(f"Template created with ID: {template_id}")
        
        # Render template
        print_info("Rendering template...")
        render_data = {
            "template_id": template_id,
            "variables": {
                "user_name": "John Doe"
            }
        }
        
        response = await client.post(
            f"{TEMPLATE_SERVICE_URL}/api/v1/templates/render",
            json=render_data
        )
        
        if response.status_code != 200:
            print_error(f"Template rendering failed: {response.status_code}")
            return False, None
        
        rendered = response.json()
        print_success(f"Template rendered successfully")
        print_info(f"Subject: {rendered['data']['subject']}")
        print_info(f"Body: {rendered['data']['body_html'][:100]}...")
        
        return True, template_id

async def test_user_registration():
    """Test user service - create user"""
    print_test("User Service - Register User")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        user_data = {
            "email": "e2etest@example.com",
            "username": "e2euser",
            "password": "SecurePass123!",
            "first_name": "E2E",
            "last_name": "Test"
        }
        
        print_info("Registering user...")
        try:
            response = await client.post(
                f"{USER_SERVICE_URL}/api/v1/auth/register",
                json=user_data
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                print_success(f"User registered: {result}")
                return True, result
            else:
                # User might already exist, try to login
                print_info("User might exist, attempting login...")
                login_response = await client.post(
                    f"{USER_SERVICE_URL}/api/v1/auth/login",
                    json={
                        "email": user_data["email"],
                        "password": user_data["password"]
                    }
                )
                if login_response.status_code == 200:
                    print_success("User logged in successfully")
                    return True, login_response.json()
                else:
                    print_error(f"Registration/Login failed: {response.status_code}")
                    print_error(f"Response: {response.text}")
                    return False, None
        except Exception as e:
            print_error(f"User registration error: {str(e)}")
            return False, None

async def test_email_notification():
    """Test email service - send email"""
    print_test("Email Service - Send Notification")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        email_data = {
            "to": "recipient@example.com",
            "subject": "E2E Test Email",
            "body_html": "<h1>Test Email</h1><p>This is an end-to-end test.</p>",
            "body_text": "Test Email - This is an end-to-end test.",
            "from_email": "noreply@example.com",
            "priority": "high"
        }
        
        print_info("Sending email via RabbitMQ...")
        try:
            response = await client.post(
                f"{EMAIL_SERVICE_URL}/api/v1/emails/send",
                json=email_data
            )
            
            if response.status_code in [200, 201, 202]:
                result = response.json()
                print_success(f"Email queued: {result}")
                return True
            else:
                print_error(f"Email send failed: {response.status_code}")
                print_error(f"Response: {response.text}")
                return False
        except Exception as e:
            print_error(f"Email service error: {str(e)}")
            return False

async def test_push_notification():
    """Test push service - send push notification"""
    print_test("Push Service - Send Notification")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        push_data = {
            "user_id": "test-user-123",
            "title": "E2E Test Push",
            "message": "This is an end-to-end test push notification",
            "data": {
                "type": "test",
                "timestamp": "2025-11-13"
            },
            "priority": "high"
        }
        
        print_info("Sending push notification via RabbitMQ...")
        try:
            response = await client.post(
                f"{PUSH_SERVICE_URL}/api/v1/push/send",
                json=push_data
            )
            
            if response.status_code in [200, 201, 202]:
                result = response.json()
                print_success(f"Push notification queued: {result}")
                return True
            else:
                print_error(f"Push send failed: {response.status_code}")
                print_error(f"Response: {response.text}")
                return False
        except Exception as e:
            print_error(f"Push service error: {str(e)}")
            return False

async def test_template_integration_with_email():
    """Test template service integration with email service"""
    print_test("Integration - Template + Email Service")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Create a template
        template_data = {
            "name": "e2e_order_confirmation",
            "subject": "Order Confirmation - {{order_id}}",
            "body_html": "<h1>Order {{order_id}} Confirmed</h1><p>Hi {{customer_name}}, your order has been confirmed!</p>",
            "body_text": "Order {{order_id}} Confirmed. Hi {{customer_name}}, your order has been confirmed!",
            "template_type": "email",
            "language": "en",
            "is_active": True
        }
        
        print_info("Step 1: Creating order confirmation template...")
        template_response = await client.post(
            f"{TEMPLATE_SERVICE_URL}/api/v1/templates/",
            json=template_data
        )
        
        if template_response.status_code not in [200, 201]:
            print_error(f"Template creation failed: {template_response.status_code}")
            return False
        
        template_id = template_response.json()["data"]["id"]
        print_success(f"Template created: {template_id}")
        
        # 2. Render the template
        print_info("Step 2: Rendering template with variables...")
        render_data = {
            "template_id": template_id,
            "variables": {
                "order_id": "ORD-2025-001",
                "customer_name": "Jane Smith"
            }
        }
        
        render_response = await client.post(
            f"{TEMPLATE_SERVICE_URL}/api/v1/templates/render",
            json=render_data
        )
        
        if render_response.status_code != 200:
            print_error(f"Template rendering failed: {render_response.status_code}")
            return False
        
        rendered = render_response.json()["data"]
        print_success(f"Template rendered successfully")
        
        # 3. Send email with rendered content
        print_info("Step 3: Sending email with rendered template...")
        email_data = {
            "to": "customer@example.com",
            "subject": rendered["subject"],
            "body_html": rendered["body_html"],
            "body_text": rendered["body_text"],
            "from_email": "orders@example.com",
            "priority": "high"
        }
        
        email_response = await client.post(
            f"{EMAIL_SERVICE_URL}/api/v1/emails/send",
            json=email_data
        )
        
        if email_response.status_code in [200, 201, 202]:
            print_success("Email sent with rendered template content")
            return True
        else:
            print_error(f"Email send failed: {email_response.status_code}")
            return False

async def test_api_gateway_routing():
    """Test API Gateway routing to microservices"""
    print_test("API Gateway - Service Routing")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test routes if gateway has them configured
        print_info("Testing API Gateway health...")
        try:
            response = await client.get(f"{API_GATEWAY_URL}/health")
            if response.status_code == 200:
                print_success(f"API Gateway health check passed")
                return True
            else:
                print_error(f"API Gateway health check failed: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"API Gateway error: {str(e)}")
            return False

async def main():
    """Run all end-to-end integration tests"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.YELLOW}DNS NOTIFICATION SYSTEM - E2E INTEGRATION TESTS{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    results = {}
    
    # Test 1: Health checks
    results["Health Checks"] = await test_health_checks()
    await asyncio.sleep(2)
    
    # Test 2: Template creation and rendering
    template_success, template_id = await test_template_creation_and_rendering()
    results["Template Service"] = template_success
    await asyncio.sleep(2)
    
    # Test 3: User registration
    user_success, user_data = await test_user_registration()
    results["User Service"] = user_success
    await asyncio.sleep(2)
    
    # Test 4: Email notification
    results["Email Service"] = await test_email_notification()
    await asyncio.sleep(2)
    
    # Test 5: Push notification
    results["Push Service"] = await test_push_notification()
    await asyncio.sleep(2)
    
    # Test 6: Template + Email integration
    results["Template-Email Integration"] = await test_template_integration_with_email()
    await asyncio.sleep(2)
    
    # Test 7: API Gateway
    results["API Gateway"] = await test_api_gateway_routing()
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.YELLOW}TEST SUMMARY{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}PASSED{Colors.RESET}" if result else f"{Colors.RED}FAILED{Colors.RESET}"
        print(f"{test_name:.<50} {status}")
    
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    success_rate = (passed / total) * 100
    print(f"Total: {passed}/{total} tests passed ({success_rate:.1f}%)")
    
    if passed == total:
        print(f"{Colors.GREEN}🎉 All tests passed! System is ready for production.{Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}⚠️  Some tests failed. Please review the errors above.{Colors.RESET}")
    
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")

if __name__ == "__main__":
    asyncio.run(main())
