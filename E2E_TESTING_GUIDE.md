# End-to-End Testing Guide - Distributed Notification System

Complete guide for testing your notification system from start to finish.

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Verification](#quick-verification)
4. [Complete E2E Test Flow](#complete-e2e-test-flow)
5. [Individual Service Testing](#individual-service-testing)
6. [Monitoring & Debugging](#monitoring--debugging)
7. [Troubleshooting](#troubleshooting)

---

## 🏗️ System Overview

Your distributed notification system consists of:

| Service              | Port        | Purpose                                |
| -------------------- | ----------- | -------------------------------------- |
| **API Gateway**      | 3000        | Main entry point, routing, idempotency |
| **User Service**     | 8001        | User management & authentication       |
| **Template Service** | 8002        | Template management & rendering        |
| **Email Service**    | 8003        | Email sending via queue                |
| **Push Service**     | 8005        | Push notification sending via queue    |
| **RabbitMQ**         | 5672, 15672 | Message queue                          |
| **PostgreSQL**       | 5432, 5433  | Database                               |
| **Redis**            | 6379        | Caching & idempotency                  |

---

## ✅ Prerequisites

Before testing, ensure:

```bash
# 1. All containers are running
docker ps

# Expected output: 8 containers running
# - api-gateway
# - user-service
# - email-service
# - push-service
# - template-service
# - rabbitmq
# - postgres
# - postgres-user
# - redis

# 2. Check container logs for errors
docker-compose logs --tail=50

# 3. Verify network connectivity
docker network inspect dns_net
```

---

## 🚀 Quick Verification

### Step 1: Health Check All Services

```bash
# API Gateway
curl http://localhost:3000/api/v1/health

# User Service
curl http://localhost:8001/api/v1/health/

# Template Service
curl http://localhost:8002/api/v1/health/

# Email Service
curl http://localhost:8003/api/v1/health/

# Push Service
curl http://localhost:8005/api/v1/health/
```

**Expected Response** (for each):

```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2025-11-14T..."
}
```

### Step 2: Check RabbitMQ Management Console

Open in browser: http://localhost:15672

- **Username**: `guest`
- **Password**: `guest`

Verify:

- Queues exist: `email.queue`, `push.queue`
- Connections from services are active
- No error messages

### Step 3: Check API Documentation

Open Swagger UI: http://localhost:3000/api/docs

You should see all available endpoints with interactive documentation.

---

## 🧪 Complete E2E Test Flow

This is the **main testing flow** that tests the entire system end-to-end.

### Test Flow Overview

```
User Registration → Login → Create Template → Send Notification → Verify Delivery
```

---

### 🔹 Test 1: Register a New User

```bash
curl -X POST http://localhost:8001/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "testuser@example.com",
    "password": "SecurePass123!",
    "preferences": {
      "email": true,
      "push": true
    }
  }'
```

**Expected Response:**

```json
{
  "success": true,
  "message": "User registered successfully",
  "data": {
    "user": {
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Test User",
      "email": "testuser@example.com",
      "email_verified": false
    },
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "verification_token": "abc123xyz..."
  }
}
```

**💾 Save these values:**

```bash
# Export for use in subsequent requests
export USER_ID="<user_id from response>"
export ACCESS_TOKEN="<access_token from response>"
```

---

### 🔹 Test 2: Login (Alternative to Registration)

If user already exists, login instead:

```bash
curl -X POST http://localhost:8001/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "SecurePass123!"
  }'
```

**Expected Response:**

```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": { ... },
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

---

### 🔹 Test 3: Get User Profile

Verify user data:

```bash
curl -X GET http://localhost:8001/api/v1/users/profile/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Response:**

```json
{
  "success": true,
  "message": "Profile retrieved successfully",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Test User",
    "email": "testuser@example.com",
    "email_verified": false,
    "push_token": null,
    "preferences": {
      "email": true,
      "push": true
    }
  }
}
```

---

### 🔹 Test 4: Create an Email Template

```bash
curl -X POST http://localhost:8002/api/v1/templates/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "welcome_email",
    "subject": "Welcome {{name}} to Our Platform!",
    "body_html": "<h1>Hello {{name}}</h1><p>Welcome to our notification system.</p><p><a href=\"{{verification_link}}\">Verify your email</a></p>",
    "body_text": "Hello {{name}}, Welcome to our notification system. Verify your email: {{verification_link}}",
    "template_type": "email",
    "language": "en",
    "variables": ["name", "verification_link"]
  }'
```

**Expected Response:**

```json
{
  "success": true,
  "message": "Template created successfully",
  "data": {
    "template_id": "660e8400-e29b-41d4-a716-446655440000",
    "name": "welcome_email",
    "subject": "Welcome {{name}} to Our Platform!",
    "template_type": "email",
    "version": 1
  }
}
```

**💾 Save template_id:**

```bash
export TEMPLATE_ID="<template_id from response>"
```

---

### 🔹 Test 5: Create a Push Notification Template

```bash
curl -X POST http://localhost:8002/api/v1/templates/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "welcome_push",
    "subject": "Welcome {{name}}!",
    "body_text": "Welcome to our platform! Tap to get started.",
    "template_type": "push",
    "language": "en",
    "variables": ["name"]
  }'
```

**Expected Response:**

```json
{
  "success": true,
  "message": "Template created successfully",
  "data": {
    "template_id": "770e8400-e29b-41d4-a716-446655440001",
    "name": "welcome_push",
    "template_type": "push",
    "version": 1
  }
}
```

**💾 Save push template_id:**

```bash
export PUSH_TEMPLATE_ID="<template_id from response>"
```

---

### 🔹 Test 6: List All Templates

```bash
curl -X GET "http://localhost:8002/api/v1/templates/?page=1&limit=10"
```

**Expected Response:**

```json
{
  "success": true,
  "message": "Retrieved 2 templates",
  "data": {
    "templates": [
      { "template_id": "...", "name": "welcome_email", ... },
      { "template_id": "...", "name": "welcome_push", ... }
    ],
    "total": 2,
    "page": 1,
    "limit": 10
  },
  "meta": {
    "total": 2,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

---

### 🔹 Test 7: Send Email Notification via API Gateway

**This is the core test - sending a notification through the gateway:**

```bash
curl -X POST http://localhost:3000/api/v1/notifications \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "notification_type": "email",
    "user_id": "'$USER_ID'",
    "template_name": "welcome_email",
    "variables": {
      "name": "Test User",
      "verification_link": "https://example.com/verify/abc123"
    },
    "priority": 1,
    "idempotency_key": "test-email-001"
  }'
```

**Expected Response:**

```json
{
  "success": true,
  "message": "email notification queued successfully",
  "data": {
    "notification_id": "880e8400-e29b-41d4-a716-446655440002",
    "status": "queued",
    "tracking_id": "880e8400-e29b-41d4-a716-446655440002"
  },
  "meta": { ... }
}
```

**💾 Save notification_id:**

```bash
export NOTIFICATION_ID="<notification_id from response>"
```

---

### 🔹 Test 8: Send Push Notification via API Gateway

```bash
curl -X POST http://localhost:3000/api/v1/notifications \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "notification_type": "push",
    "user_id": "'$USER_ID'",
    "template_name": "welcome_push",
    "variables": {
      "name": "Test User"
    },
    "priority": 1,
    "idempotency_key": "test-push-001"
  }'
```

**Expected Response:**

```json
{
  "success": true,
  "message": "push notification queued successfully",
  "data": {
    "notification_id": "990e8400-e29b-41d4-a716-446655440003",
    "status": "queued",
    "tracking_id": "990e8400-e29b-41d4-a716-446655440003"
  }
}
```

**💾 Save push notification_id:**

```bash
export PUSH_NOTIFICATION_ID="<notification_id from response>"
```

---

### 🔹 Test 9: Check Notification Status

Wait a few seconds, then check status:

```bash
# Check email notification status
curl -X GET "http://localhost:3000/api/v1/notifications/$NOTIFICATION_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Check push notification status
curl -X GET "http://localhost:3000/api/v1/notifications/$PUSH_NOTIFICATION_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Response:**

```json
{
  "success": true,
  "message": "Notification status retrieved successfully",
  "data": {
    "notification_id": "880e8400-e29b-41d4-a716-446655440002",
    "status": "sent", // or "processing", "delivered", "failed"
    "notification_type": "email",
    "created_at": "2025-11-14T...",
    "sent_at": "2025-11-14T..."
  }
}
```

**Status Values:**

- `queued`: In RabbitMQ, waiting to be processed
- `processing`: Being sent right now
- `sent`: Successfully sent
- `delivered`: Confirmed delivery (email opened, push received)
- `failed`: Permanent failure

---

### 🔹 Test 10: List All Notifications

```bash
curl -X GET "http://localhost:3000/api/v1/notifications?page=1&limit=10" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Response:**

```json
{
  "success": true,
  "message": "Notifications retrieved successfully",
  "data": [
    {
      "notification_id": "...",
      "notification_type": "email",
      "status": "sent",
      ...
    },
    {
      "notification_id": "...",
      "notification_type": "push",
      "status": "sent",
      ...
    }
  ],
  "meta": {
    "total": 2,
    "page": 1,
    "limit": 10,
    "total_pages": 1
  }
}
```

---

### 🔹 Test 11: Test Idempotency

Send the **exact same request** again with the same `idempotency_key`:

```bash
curl -X POST http://localhost:3000/api/v1/notifications \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "notification_type": "email",
    "user_id": "'$USER_ID'",
    "template_name": "welcome_email",
    "variables": {
      "name": "Test User",
      "verification_link": "https://example.com/verify/abc123"
    },
    "priority": 1,
    "idempotency_key": "test-email-001"
  }'
```

**Expected Response:**

```json
{
  "success": true,
  "message": "email notification queued successfully",
  "data": {
    "notification_id": "880e8400-e29b-41d4-a716-446655440002", // SAME ID as before
    "status": "sent", // Already sent
    "is_duplicate": true // May include this flag
  }
}
```

**✅ Success Criteria:** The notification should NOT be sent again. Same notification_id returned.

---

### 🔹 Test 12: Test User Preferences

Update user preferences to disable email:

```bash
curl -X PATCH http://localhost:8001/api/v1/users/preferences/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "email": false,
    "push": true
  }'
```

Now try sending an email notification - it should be filtered:

```bash
curl -X POST http://localhost:3000/api/v1/notifications \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "notification_type": "email",
    "user_id": "'$USER_ID'",
    "template_name": "welcome_email",
    "variables": {
      "name": "Test User",
      "verification_link": "https://example.com/verify/abc123"
    },
    "idempotency_key": "test-email-002"
  }'
```

**Expected Behavior:** The notification may be queued but should not be sent (filtered by email service based on user preferences).

---

## 🔍 Individual Service Testing

### Template Service Direct Testing

```bash
# Create template
curl -X POST http://localhost:8002/api/v1/templates/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_template",
    "subject": "Test {{variable}}",
    "body_html": "<p>Hello {{name}}</p>",
    "body_text": "Hello {{name}}",
    "template_type": "email"
  }'

# Get template by ID
curl http://localhost:8002/api/v1/templates/$TEMPLATE_ID

# Get template by name
curl http://localhost:8002/api/v1/templates/name/welcome_email

# Render template (test variable substitution)
curl -X POST http://localhost:8002/api/v1/render/ \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "welcome_email",
    "variables": {
      "name": "John Doe",
      "verification_link": "https://example.com/verify/xyz"
    }
  }'

# Expected: Rendered HTML and text with variables replaced
```

### User Service Direct Testing

```bash
# Create user
curl -X POST http://localhost:8001/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Direct Test User",
    "email": "direct@example.com",
    "password": "Password123!"
  }'

# Login
curl -X POST http://localhost:8001/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "direct@example.com",
    "password": "Password123!"
  }'

# Update profile
curl -X PATCH http://localhost:8001/api/v1/users/profile/ \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "push_token": "fcm_token_example"
  }'
```

### Test RabbitMQ Message Publishing

Using the test endpoint in User Service:

```bash
curl -X POST http://localhost:8001/api/v1/notifications/test/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$USER_ID'",
    "template_code": "WELCOME_TEST",
    "variables": {
      "name": "Test User"
    },
    "priority": 1
  }'
```

**Expected Response:**

```json
{
  "success": true,
  "message": "Test notification published",
  "data": {
    "message": "Test notification published",
    "payload": { ... }
  }
}
```

---

## 📊 Monitoring & Debugging

### 1. Check RabbitMQ Queue Status

Open: http://localhost:15672

Navigate to **Queues** tab:

- `email.queue` - Check message count
- `push.queue` - Check message count

**Healthy State:**

- Messages should be processed quickly (count goes to 0)
- No messages in Dead Letter Queue (DLQ)
- Consumer count > 0

### 2. View Service Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api-gateway
docker-compose logs -f user-service
docker-compose logs -f email-service
docker-compose logs -f push-service
docker-compose logs -f template-service

# Filter by errors only
docker-compose logs | grep ERROR

# Last 100 lines
docker-compose logs --tail=100
```

### 3. Check PostgreSQL Database

```bash
# Connect to main database
docker exec -it postgres psql -U postgres -d notification_db

# Connect to user service database
docker exec -it postgres-user psql -U postgres -d user_db

# Sample queries:
# \dt                        -- List all tables
# SELECT * FROM notifications LIMIT 10;
# SELECT * FROM users LIMIT 10;
# SELECT * FROM templates LIMIT 10;
# \q                         -- Exit
```

### 4. Check Redis Cache

```bash
# Connect to Redis
docker exec -it redis redis-cli

# Sample commands:
# KEYS *                     -- List all keys
# GET user_preferences:<user_id>
# TTL <key>                  -- Check time to live
# FLUSHDB                    -- Clear database (CAREFUL!)
# EXIT
```

### 5. API Gateway Logs

Check specific log files:

```bash
# View combined logs
docker exec -it <api-gateway-container-id> cat logs/combined.log

# View error logs only
docker exec -it <api-gateway-container-id> cat logs/error.log

# Tail logs in real-time
docker exec -it <api-gateway-container-id> tail -f logs/combined.log
```

---

## 🛠️ Troubleshooting

### Issue: "Connection Refused" Errors

**Symptoms:** Services can't connect to each other

**Solutions:**

1. Check if all containers are running:

   ```bash
   docker ps
   ```

2. Check container networking:

   ```bash
   docker network inspect dns_net
   ```

3. Verify service hostnames in docker-compose.yml

4. Restart specific service:
   ```bash
   docker-compose restart <service-name>
   ```

---

### Issue: RabbitMQ Messages Not Being Consumed

**Symptoms:** Messages stay in queue, not processed

**Solutions:**

1. Check consumer services are running:

   ```bash
   docker-compose logs email-service | grep "consumer"
   docker-compose logs push-service | grep "consumer"
   ```

2. Verify consumers in RabbitMQ Management UI:

   - Go to http://localhost:15672
   - Check "Queues" tab
   - Each queue should show "1 consumer" or more

3. Restart consumer services:

   ```bash
   docker-compose restart email-service push-service
   ```

4. Check for errors in consumer logs:
   ```bash
   docker-compose logs email-service --tail=100 | grep ERROR
   ```

---

### Issue: Notifications Marked as "Failed"

**Symptoms:** Status shows "failed" in tracking

**Solutions:**

1. Check service logs for errors:

   ```bash
   docker-compose logs email-service --tail=100
   docker-compose logs push-service --tail=100
   ```

2. Common causes:

   - **Template not found**: Create the template first
   - **Invalid template variables**: Ensure all required variables are provided
   - **User not found**: Verify user_id exists
   - **Email provider issues**: Check email service configuration
   - **Push token missing**: Ensure user has a valid push_token

3. Check Dead Letter Queue (DLQ) in RabbitMQ

---

### Issue: "Template Not Found" Error

**Symptoms:** Error when sending notification

**Solutions:**

1. List all templates:

   ```bash
   curl http://localhost:8002/api/v1/templates/
   ```

2. Verify template name matches exactly (case-sensitive)

3. Create missing template:
   ```bash
   curl -X POST http://localhost:8002/api/v1/templates/ \
     -H "Content-Type: application/json" \
     -d '{ "name": "your_template_name", ... }'
   ```

---

### Issue: Authentication Failures

**Symptoms:** 401 Unauthorized errors

**Solutions:**

1. Verify token is valid:

   ```bash
   echo $ACCESS_TOKEN
   ```

2. Re-login to get new token:

   ```bash
   curl -X POST http://localhost:8001/api/v1/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"email": "...", "password": "..."}'
   ```

3. Check token format in Authorization header:
   ```
   Authorization: Bearer <token>
   ```

---

### Issue: Database Connection Errors

**Symptoms:** Services can't connect to PostgreSQL

**Solutions:**

1. Check PostgreSQL containers:

   ```bash
   docker ps | grep postgres
   ```

2. Test connection:

   ```bash
   docker exec -it postgres psql -U postgres -c "SELECT 1;"
   ```

3. Verify environment variables in .env files

4. Restart database:
   ```bash
   docker-compose restart postgres postgres-user
   ```

---

### Issue: Redis Connection Errors

**Symptoms:** Caching/idempotency not working

**Solutions:**

1. Check Redis is running:

   ```bash
   docker ps | grep redis
   ```

2. Test connection:

   ```bash
   docker exec -it redis redis-cli PING
   # Expected: PONG
   ```

3. Restart Redis:
   ```bash
   docker-compose restart redis
   ```

---

## 🧹 Cleanup & Reset

### Reset All Data

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: Deletes all data!)
docker-compose down -v

# Rebuild and restart
docker-compose up --build -d
```

### Clear Redis Cache Only

```bash
docker exec -it redis redis-cli FLUSHDB
```

### Clear RabbitMQ Queues

Via Management UI: http://localhost:15672

1. Go to "Queues" tab
2. Click on queue name
3. Click "Purge Messages"

---

## 📝 Quick Test Script

Save this as `test_e2e.sh` for automated testing:

```bash
#!/bin/bash

set -e  # Exit on error

BASE_URL_GATEWAY="http://localhost:3000/api/v1"
BASE_URL_USER="http://localhost:8001/api/v1"
BASE_URL_TEMPLATE="http://localhost:8002/api/v1"

echo "🚀 Starting E2E Tests..."

# 1. Health checks
echo "✅ Checking health endpoints..."
curl -s "$BASE_URL_GATEWAY/health" | jq '.status'
curl -s "$BASE_URL_USER/health/" | jq '.status'
curl -s "$BASE_URL_TEMPLATE/health/" | jq '.status'

# 2. Create user
echo "👤 Creating test user..."
USER_RESPONSE=$(curl -s -X POST "$BASE_URL_USER/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E2E Test User",
    "email": "e2e-test-'$(date +%s)'@example.com",
    "password": "SecurePass123!",
    "preferences": {"email": true, "push": true}
  }')

USER_ID=$(echo $USER_RESPONSE | jq -r '.data.user.user_id')
ACCESS_TOKEN=$(echo $USER_RESPONSE | jq -r '.data.access_token')

echo "User ID: $USER_ID"
echo "Token: ${ACCESS_TOKEN:0:20}..."

# 3. Create template
echo "📝 Creating email template..."
TEMPLATE_RESPONSE=$(curl -s -X POST "$BASE_URL_TEMPLATE/templates/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_email_'$(date +%s)'",
    "subject": "Test {{name}}",
    "body_html": "<p>Hello {{name}}</p>",
    "body_text": "Hello {{name}}",
    "template_type": "email"
  }')

TEMPLATE_NAME=$(echo $TEMPLATE_RESPONSE | jq -r '.data.name')
echo "Template: $TEMPLATE_NAME"

# 4. Send notification
echo "📧 Sending notification..."
NOTIF_RESPONSE=$(curl -s -X POST "$BASE_URL_GATEWAY/notifications" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "notification_type": "email",
    "user_id": "'$USER_ID'",
    "template_name": "'$TEMPLATE_NAME'",
    "variables": {"name": "E2E Test User"},
    "idempotency_key": "e2e-test-'$(date +%s)'"
  }')

NOTIFICATION_ID=$(echo $NOTIF_RESPONSE | jq -r '.data.notification_id')
echo "Notification ID: $NOTIFICATION_ID"

# 5. Check status
echo "🔍 Checking notification status..."
sleep 3  # Wait for processing
STATUS_RESPONSE=$(curl -s "$BASE_URL_GATEWAY/notifications/$NOTIFICATION_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo $STATUS_RESPONSE | jq '.data.status'

echo "✅ E2E Test Complete!"
```

Make it executable and run:

```bash
chmod +x test_e2e.sh
./test_e2e.sh
```

---

## 🎯 Success Criteria Checklist

- [ ] All 8 containers running (`docker ps`)
- [ ] All health endpoints return "healthy"
- [ ] Can register new user
- [ ] Can login and get JWT token
- [ ] Can create email template
- [ ] Can create push template
- [ ] Can send notification via API Gateway
- [ ] Notification status changes from "queued" to "sent"
- [ ] RabbitMQ queues are being consumed (message count = 0)
- [ ] Can retrieve notification status by ID
- [ ] Idempotency works (duplicate requests return same ID)
- [ ] User preferences are respected
- [ ] Swagger docs accessible at http://localhost:3000/api/docs

---

## 📚 Additional Resources

- **Swagger API Docs**: http://localhost:3000/api/docs
- **RabbitMQ Management**: http://localhost:15672
- **Service README files**: Check each service directory for detailed docs
- **Architecture Docs**: See `services/user-service/ARCHITECTURE.md`

---

## 🤝 Support

If you encounter issues not covered in this guide:

1. Check service-specific README files
2. Review docker-compose logs
3. Verify environment variables in .env files
4. Ensure ports are not already in use
5. Check Docker resources (memory, CPU)

---

**Last Updated**: November 14, 2025
**Version**: 1.0.0
