# User Service - Django REST Framework

Complete user management and authentication service for the Distributed Notification System.

## 🚀 Features

- ✅ User registration with email verification
- ✅ JWT-based authentication (access + refresh tokens)
- ✅ Password reset flow
- ✅ User profile management (CRUD operations)
- ✅ Notification preferences (email/push toggle)
- ✅ RabbitMQ consumer for push notification requests
- ✅ Redis caching for user preferences
- ✅ Circuit breaker pattern for external services
- ✅ Idempotency using `X-Request-ID` header
- ✅ Correlation IDs for distributed tracing
- ✅ Health check endpoint
- ✅ Comprehensive test suite
- ✅ Docker support with docker-compose
- ✅ OpenAPI/Swagger documentation

## 📋 Tech Stack

- **Framework**: Django 5.0 + Django REST Framework
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Message Queue**: RabbitMQ 3.12
- **Authentication**: JWT (SimpleJWT)
- **Testing**: pytest + pytest-django
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions

## 🏗️ Architecture

```
┌─────────────────┐
│   API Gateway   │
└────────┬────────┘
         │
    ┌────▼────┐
    │  User   │◄──────── PostgreSQL
    │ Service │◄──────── Redis Cache
    └────┬────┘
         │
         └───────────► RabbitMQ (push.queue)
```

## 📁 Project Structure

```
user-service/
├── user_service/           # Django project settings
│   ├── settings.py        # Configuration
│   ├── urls.py            # URL routing
│   └── wsgi.py            # WSGI entry point
├── users/                 # Main app
│   ├── models.py          # User, UserPreference, IdempotencyKey
│   ├── serializers.py     # DRF serializers
│   ├── views.py           # API endpoints
│   ├── urls.py            # App URLs
│   ├── middleware.py      # Correlation ID middleware
│   ├── pagination.py      # Custom pagination
│   ├── decorators.py      # Idempotency decorator
│   ├── rabbitmq_consumer.py  # RabbitMQ consumer
│   └── tests/             # Test suite
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container definition
├── docker-compose.yml     # Multi-container setup
├── pytest.ini             # Pytest configuration
└── README.md              # This file
```

## 🔧 Setup & Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- RabbitMQ 3.12+
- Docker & Docker Compose (optional)


### JWT Authentication

This service uses JWT (JSON Web Tokens) for authentication. Upon successful login or registration, the API returns a single access token. Use this token to authenticate all API requests. There is no refresh token; when the access token expires, the user must log in again to obtain a new one.

#### Login Example

```
POST /api/v1/auth/login/
{
  "email": "user@example.com",
  "password": "password123"
}
```

Response:
```
{
  "user": { ... },
  "access_token": "<access_token>"
}
```

#### Using the Access Token

Include the access token in the `Authorization` header for authenticated requests:

```
Authorization: Bearer <access_token>
```

2. **Run migrations**
```bash
docker-compose exec user_service python manage.py migrate
```

3. **Create superuser**
```bash
docker-compose exec user_service python manage.py createsuperuser
```

4. **View logs**
```bash
docker-compose logs -f user_service
```

5. **Stop services**
```bash
docker-compose down
```

## 📚 API Documentation

Access Swagger UI at: `http://localhost:8000/swagger/`  
Access ReDoc at: `http://localhost:8000/redoc/`

### Base URL
```
http://localhost:8000/api/v1/
```

### Response Format

All responses follow this standardized format:

```json
{
  "success": true,
  "message": "Success message",
  "data": { ... },
  "meta": {
    "total": 100,
    "limit": 20,
    "page": 1,
    "total_pages": 5,
    "has_next": true,
    "has_previous": false
  }
}
```

### Endpoints

#### Authentication

**Register User**
```http
POST /api/v1/users/
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "push_token": "fcm_token_here",
  "preferences": {
    "email": true,
    "push": true
  }
}
```

**Login**
```http
POST /api/v1/auth/login/
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "SecurePass123!"
}
```

**Refresh Token**
```http
POST /api/v1/auth/refresh/
Content-Type: application/json

{
  "refresh": "your_refresh_token"
}
```

**Verify Email**
```http
POST /api/v1/auth/verify-email/
Content-Type: application/json

{
  "token": "verification_token"
}
```

**Password Reset Request**
```http
POST /api/v1/auth/password-reset/
Content-Type: application/json

{
  "email": "john@example.com"
}
```

**Password Reset Confirm**
```http
POST /api/v1/auth/password-reset/confirm/
Content-Type: application/json

{
  "token": "reset_token",
  "password": "NewSecurePass123!",
  "password_confirm": "NewSecurePass123!"
}
```

#### User Management

**Get Profile** (requires authentication)
```http
GET /api/v1/users/profile/
Authorization: Bearer <access_token>
```

**Update Profile**
```http
PATCH /api/v1/users/profile/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "Jane Doe",
  "push_token": "new_fcm_token"
}
```

**Delete Account** (soft delete)
```http
DELETE /api/v1/users/profile/
Authorization: Bearer <access_token>
```

#### Preferences

**Get Preferences**
```http
GET /api/v1/users/preferences/
Authorization: Bearer <access_token>
```

**Update Preferences**
```http
PATCH /api/v1/users/preferences/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "email": false,
  "push": true
}
```

#### Health Check

```http
GET /api/v1/health/
```

## 🔐 Authentication

This service uses JWT (JSON Web Tokens) for authentication:

1. Login to receive `access` and `refresh` tokens
2. Include access token in requests: `Authorization: Bearer <token>`
3. Access tokens expire after 60 minutes (configurable)
4. Refresh tokens expire after 24 hours (configurable)
5. Use refresh token to get new access token

## 🎯 Idempotency

Prevent duplicate operations by including the `X-Request-ID` header:

```http
POST /api/v1/users/
X-Request-ID: unique-request-id-12345
Content-Type: application/json

{...}
```

Identical requests with the same `X-Request-ID` within 24 hours will return the cached response.

## 📊 Correlation IDs

All requests are assigned a correlation ID for distributed tracing:

- Include `X-Correlation-ID` header in requests (optional)
- Response includes `X-Correlation-ID` header
- All logs include the correlation ID

## 🐰 RabbitMQ Consumer

The service consumes messages from the `push.queue` to handle push notification requests.

**Message Format:**
```json
{
  "notification_type": "push",
  "user_id": "uuid",
  "template_code": "welcome_notification",
  "variables": {
    "name": "John",
    "link": "https://example.com"
  },
  "request_id": "unique-id",
  "priority": 1,
  "metadata": {}
}
```

**Consumer Features:**
- Fetches user preferences from cache/DB
- Validates user has push notifications enabled
- Checks for push token
- Implements exponential backoff retry
- Circuit breaker for reliability

**Run Consumer:**
```bash
python manage.py consume_rabbitmq
```

## 🧪 Testing

Run the full test suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov --cov-report=html
```

Run specific tests:

```bash
pytest users/tests/test_models.py
pytest users/tests/test_api.py
```

Run with markers:

```bash
pytest -m unit
pytest -m integration
```

## 📦 Database Models

### User
- `id` (UUID): Primary key
- `email` (Email): Unique, indexed
- `name` (String): User's full name
- `password` (String): Hashed password
- `push_token` (String): FCM/APNS token
- `preferences` (FK): User preferences
- `email_verified` (Boolean): Email verification status
- `is_active` (Boolean): Account status
- `created_at`, `updated_at` (DateTime): Timestamps

### UserPreference
- `id` (UUID): Primary key
- `email` (Boolean): Email notifications enabled
- `push` (Boolean): Push notifications enabled
- `created_at`, `updated_at` (DateTime): Timestamps

### IdempotencyKey
- `id` (UUID): Primary key
- `request_id` (String): Unique request identifier
- `endpoint` (String): API endpoint
- `response_data` (JSON): Cached response
- `status_code` (Integer): HTTP status
- `expires_at` (DateTime): Expiration time

## 🚀 Deployment

### Environment Variables

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com

# Database
DB_NAME=user_service_db
DB_USER=postgres
DB_PASSWORD=secure_password
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
```

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Use strong database passwords
- [ ] Enable HTTPS
- [ ] Configure CORS properly
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy
- [ ] Set up rate limiting
- [ ] Review security settings

## 📈 Performance Targets

- ✅ Handle 1,000+ requests per minute
- ✅ API response time < 100ms (cached)
- ✅ API response time < 500ms (uncached)
- ✅ 99.5% availability
- ✅ Horizontal scaling support

## 🔍 Monitoring

### Health Check

```http
GET /api/v1/health/
```

Returns:
```json
{
  "success": true,
  "data": {
    "service": "user-service",
    "status": "healthy",
    "timestamp": "2025-11-11T12:00:00Z",
    "checks": {
      "database": "healthy",
      "cache": "healthy"
    }
  }
}
```

### Logs

Logs are output in JSON format for easy parsing:

```json
{
  "timestamp": "2025-11-11T12:00:00Z",
  "level": "INFO",
  "logger": "users.views",
  "message": "User logged in",
  "correlation_id": "abc-123",
  "user_id": "uuid"
}
```

## 🛡️ Security Features

- ✅ Password hashing (Django's default PBKDF2)
- ✅ JWT token-based authentication
- ✅ CORS protection
- ✅ SQL injection protection (ORM)
- ✅ XSS protection
- ✅ CSRF protection
- ✅ Rate limiting (via Redis)
- ✅ Input validation
- ✅ Secure password requirements

## 🤝 Contributing

Follow conventional commits:

```
feat(auth): add password reset functionality
fix(api): resolve null pointer in user service
docs(readme): update API documentation
test(users): add integration tests
```

## 📝 License

MIT License

## 👥 Authors

- Your Team Name

## 📞 Support

For issues and questions, please open an issue on GitHub or contact the team.

---

**Note**: This service is part of the Distributed Notification System internship project.
