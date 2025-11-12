# API Examples for Testing

## Register a New User

```powershell
$body = @{
    name = "John Doe"
    email = "john.doe@example.com"
    password = "SecurePass123!"
    preferences = @{
        email = $true
        push = $true
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/users/" -Method POST -Body $body -ContentType "application/json"
```

## Login

```powershell
$loginBody = @{
    email = "john.doe@example.com"
    password = "SecurePass123!"
} | ConvertTo-Json

$loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login/" -Method POST -Body $loginBody -ContentType "application/json"
$accessToken = $loginResponse.data.tokens.access
```

## Get User Profile

```powershell
$headers = @{
    Authorization = "Bearer $accessToken"
}

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/users/profile/" -Method GET -Headers $headers
```

## Update User Profile

```powershell
$updateBody = @{
    name = "Jane Doe"
    push_token = "fcm_token_12345"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/users/profile/" -Method PATCH -Body $updateBody -ContentType "application/json" -Headers $headers
```

## Update Preferences

```powershell
$prefsBody = @{
    email = $false
    push = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/users/preferences/" -Method PATCH -Body $prefsBody -ContentType "application/json" -Headers $headers
```

## Health Check

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health/" -Method GET
```

## Publish Test Message to RabbitMQ

```powershell
# Note: Requires RabbitMQ client library or REST API plugin
# This is a conceptual example - actual implementation depends on your setup

$message = @{
    notification_type = "push"
    user_id = "your-user-uuid-here"
    template_code = "test_notification"
    variables = @{
        name = "John"
        link = "https://example.com"
    }
    request_id = "test-request-123"
    priority = 1
} | ConvertTo-Json

# Publish to push.queue via RabbitMQ Management API
$rabbitmqAuth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("guest:guest"))
$rabbitmqHeaders = @{
    Authorization = "Basic $rabbitmqAuth"
    "Content-Type" = "application/json"
}

$publishBody = @{
    properties = @{}
    routing_key = "push.queue"
    payload = $message
    payload_encoding = "string"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:15672/api/exchanges/%2F/notifications.direct/publish" -Method POST -Body $publishBody -Headers $rabbitmqHeaders
```
