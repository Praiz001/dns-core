# Email Service

A microservice for processing and sending email notifications in a distributed notification system.

## Features

- **RabbitMQ Integration**: Consumes email notifications from message queue
- **Multiple Email Providers**: Supports SMTP and SendGrid with strategy pattern
- **Resilience**: Circuit breakers, retry logic with exponential backoff
- **Caching**: Redis caching for user preferences
- **Database**: PostgreSQL with Alembic migrations
- **Observability**: Structured logging and health checks
- **Webhooks**: Email delivery status tracking

## Architecture

The service follows clean architecture principles with clear separation of concerns:

```
app/
├── api/              # API endpoints and dependencies
├── consumers/        # RabbitMQ message consumers
├── providers/        # Email provider implementations (Strategy pattern)
├── services/         # Business logic layer
├── db/               # Database layer (Repository pattern)
├── models/           # SQLAlchemy models
├── schemas/          # Pydantic schemas
└── utils/            # Utilities (logging, cache, circuit breaker)
```

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL
- RabbitMQ
- Redis

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Update `.env` with your configuration

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start the service:
```bash
uvicorn app.main:app --reload --port 8003
```

## Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback migration:
```bash
alembic downgrade -1
```

## Email Providers

### SMTP
Configure in `.env`:
```
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
```

### SendGrid
Configure in `.env`:
```
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=your-api-key
```

## Testing

Run tests:
```bash
pytest
```

With coverage:
```bash
pytest --cov=app tests/
```

## API Endpoints

- `GET /` - Service info
- `GET /api/v1/health` - Health check
- `POST /api/v1/webhooks/email` - Email provider webhooks
- `GET /docs` - Swagger documentation (dev only)

## Design Patterns

- **Strategy Pattern**: Email providers (SMTP, SendGrid)
- **Repository Pattern**: Database access layer
- **Dependency Injection**: FastAPI Depends
- **Circuit Breaker**: Failure handling
- **Retry Pattern**: Exponential backoff

## Environment Variables

See `.env.example` for all configuration options.

## License

MIT
