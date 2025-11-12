# Push Notification Service

Push notification microservice for the Distributed Notification System. Handles push notifications via Firebase Cloud Messaging (FCM) and OneSignal.

## Features

- ✅ Consume messages from RabbitMQ `push.queue`
- ✅ Fetch user push tokens and preferences
- ✅ Render notification templates
- ✅ Send push notifications via FCM
- ✅ Retry logic with exponential backoff
- ✅ Circuit breaker for FCM calls
- ✅ Update notification status in API Gateway
- ✅ Log deliveries to database
- ✅ Dead Letter Queue (DLQ) handling

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL (async with SQLAlchemy)
- **Message Queue**: RabbitMQ (aio-pika)
- **Push Providers**: Firebase Cloud Messaging (FCM)
- **Resilience**: Tenacity (retry), PyBreaker (circuit breaker)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Run Database Migrations

```bash
alembic upgrade head
```

### 4. Start Service

```bash
uvicorn app.main:app --reload --port 8004
```

## API Endpoints

- `GET /` - Service info
- `GET /api/v1/health` - Health check

## Architecture

```
RabbitMQ Queue (push.queue)
    ↓
Push Consumer
    ↓
Push Service
    ├─→ User Service (get preferences & push token)
    ├─→ Template Service (render template)
    ├─→ FCM Provider (send notification)
    ├─→ Database (log delivery)
    └─→ API Gateway (update status)
```

## Environment Variables

See `.env.example` for all configuration options.

## Testing

```bash
# Run unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=app --cov-report=html
```

## Docker

```bash
# Build image
docker build -t push-service .

# Run container
docker run -p 8004:8000 --env-file .env push-service
```
