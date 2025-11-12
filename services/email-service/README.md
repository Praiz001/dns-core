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
- UV (recommended) or pip

### Installation

#### Option 1: Using UV (Recommended)

UV is a fast Python package installer and resolver, 10-100x faster than pip.

1. Install UV:
```bash
pip install uv
```

2. Install dependencies:
```bash
uv sync
```

3. Copy environment variables:
```bash
cp .env.example .env
```

4. Update `.env` with your configuration

See [UV_GUIDE.md](./UV_GUIDE.md) for detailed UV usage instructions.

#### Option 2: Using pip

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy environment variables:
```bash
cp .env.example .env
```

4. Update `.env` with your configuration

5. Run database migrations:
```bash
# With UV
uv run alembic upgrade head

# With pip
alembic upgrade head
```

6. Start the service:
```bash
# With UV
uv run uvicorn app.main:app --reload --port 8003

# With pip
uvicorn app.main:app --reload --port 8003
```

## Database Migrations

Create a new migration:
```bash
# With UV
uv run alembic revision --autogenerate -m "description"

# With pip
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
# With UV
uv run alembic upgrade head

# With pip
alembic upgrade head
```

Rollback migration:
```bash
# With UV
uv run alembic downgrade -1

# With pip
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
# With UV
uv run pytest

# With pip
pytest
```

With coverage:
```bash
# With UV
uv run pytest --cov=app tests/

# With pip
pytest --cov=app tests/
```

Run specific test suites:
```bash
# Unit tests only
uv run pytest tests/unit/ -v

# Integration tests only
uv run pytest tests/integration/ -v

# With coverage report
uv run pytest --cov=app --cov-report=html tests/
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
