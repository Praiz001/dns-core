# User Service - Quick Reference Guide

## 🚀 Quick Start (PowerShell)

```powershell
# Navigate to user service
cd services\user-service

# Run quick start script
.\start.ps1
```

## 📋 Common Commands

### Docker Commands

```powershell
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f user_service

# Stop all services
docker-compose down

# Restart a service
docker-compose restart user_service

# Run migrations
docker-compose exec user_service python manage.py migrate

# Create superuser
docker-compose exec user_service python manage.py createsuperuser

# Access Django shell
docker-compose exec user_service python manage.py shell

# Run tests
docker-compose exec user_service pytest
```

### Local Development

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start dev server
python manage.py runserver

# Run consumer (separate terminal)
python manage.py consume_rabbitmq

# Run tests
pytest

# Format code
black .
isort .
```

## 🔑 Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Required
SECRET_KEY=your-secret-key-change-in-production
DB_NAME=user_service_db
DB_PASSWORD=secure_password

# Optional (defaults work for local development)
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_USER=postgres
DB_HOST=localhost
DB_PORT=5432
REDIS_HOST=localhost
REDIS_PORT=6379
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
```

## 📊 API Endpoints Quick Reference

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| POST | `/api/v1/users/` | No | Register new user |
| POST | `/api/v1/auth/login/` | No | Login user |
| POST | `/api/v1/auth/refresh/` | No | Refresh token |
| POST | `/api/v1/auth/verify-email/` | No | Verify email |
| POST | `/api/v1/auth/password-reset/` | No | Request password reset |
| POST | `/api/v1/auth/password-reset/confirm/` | No | Confirm password reset |
| GET | `/api/v1/users/profile/` | Yes | Get user profile |
| PATCH | `/api/v1/users/profile/` | Yes | Update profile |
| DELETE | `/api/v1/users/profile/` | Yes | Delete account |
| GET | `/api/v1/users/preferences/` | Yes | Get preferences |
| PATCH | `/api/v1/users/preferences/` | Yes | Update preferences |
| GET | `/api/v1/health/` | No | Health check |

## 🧪 Testing Workflow

```powershell
# Run all tests
pytest

# Run specific test file
pytest users/tests/test_models.py

# Run with coverage
pytest --cov --cov-report=html

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# View coverage report
start htmlcov/index.html
```

## 🐛 Troubleshooting

### Database Connection Error

```powershell
# Check if PostgreSQL is running
docker-compose ps

# Restart database
docker-compose restart db

# Check logs
docker-compose logs db
```

### Redis Connection Error

```powershell
# Check if Redis is running
docker-compose ps

# Test Redis connection
docker-compose exec redis redis-cli ping

# Restart Redis
docker-compose restart redis
```

### RabbitMQ Connection Error

```powershell
# Check RabbitMQ status
docker-compose ps

# Access RabbitMQ Management UI
# http://localhost:15672 (guest/guest)

# Restart RabbitMQ
docker-compose restart rabbitmq
```

### Migration Issues

```powershell
# Reset migrations (CAUTION: deletes all data)
docker-compose down -v
docker-compose up -d
docker-compose exec user_service python manage.py migrate
```

## 📝 Code Quality

```powershell
# Check code style
flake8 .

# Format code
black .
isort .

# Type checking (if mypy installed)
mypy users/
```

## 🔐 Security Checklist

Before deploying to production:

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS` properly
- [ ] Use strong database passwords
- [ ] Enable HTTPS
- [ ] Review CORS settings
- [ ] Set up rate limiting
- [ ] Configure secure session cookies
- [ ] Enable Django security middleware
- [ ] Review JWT token expiration times

## 📦 Dependency Management

```powershell
# Add new package
pip install package-name
pip freeze > requirements.txt

# Update all packages
pip install --upgrade -r requirements.txt
```

## 🔄 Database Operations

```powershell
# Create new migration
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Rollback migration
python manage.py migrate users 0001_initial

# Show migrations
python manage.py showmigrations

# SQL for migration
python manage.py sqlmigrate users 0001
```

## 📊 Useful SQL Queries

```sql
-- Count users
SELECT COUNT(*) FROM users;

-- Find unverified users
SELECT email, created_at FROM users WHERE email_verified = false;

-- Check preferences distribution
SELECT 
    SUM(CASE WHEN email = true THEN 1 ELSE 0 END) as email_enabled,
    SUM(CASE WHEN push = true THEN 1 ELSE 0 END) as push_enabled
FROM user_preferences;

-- Active users in last 7 days
SELECT COUNT(*) FROM users 
WHERE last_login >= NOW() - INTERVAL '7 days';
```

## 🎯 Performance Tips

1. **Use caching**: User preferences are cached in Redis for 1 hour
2. **Database indexes**: Email and created_at fields are indexed
3. **Connection pooling**: Configured in Django settings
4. **Async workers**: Use multiple Gunicorn workers
5. **RabbitMQ QoS**: Set prefetch_count to control concurrent messages

## 📈 Monitoring

```powershell
# Check service health
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health/"

# View logs in real-time
docker-compose logs -f --tail=100 user_service

# Check resource usage
docker stats user_service_api
```

## 🔗 Useful Links

- **Swagger UI**: http://localhost:8000/swagger/
- **ReDoc**: http://localhost:8000/redoc/
- **Django Admin**: http://localhost:8000/admin/
- **RabbitMQ Management**: http://localhost:15672/
- **Health Check**: http://localhost:8000/api/v1/health/

## 💡 Tips & Best Practices

1. Always use correlation IDs for tracking requests
2. Include `X-Request-ID` header for idempotency
3. Use pagination for list endpoints
4. Follow snake_case naming convention
5. Write meaningful commit messages (conventional commits)
6. Test endpoints with Swagger UI before integrating
7. Monitor RabbitMQ queue lengths
8. Keep Redis memory usage in check
9. Backup PostgreSQL database regularly
10. Use environment-specific settings

## 🆘 Getting Help

1. Check the logs: `docker-compose logs -f user_service`
2. Review API documentation: http://localhost:8000/swagger/
3. Check health endpoint: http://localhost:8000/api/v1/health/
4. Verify environment variables in `.env`
5. Consult README.md for detailed documentation

## 📞 Team Communication

Follow conventional commit format for all commits:

```
feat(auth): add password reset functionality
fix(api): resolve null pointer exception
docs(readme): update API documentation
test(users): add integration tests
refactor(models): optimize user queries
perf(cache): improve cache hit rate
chore(deps): update dependencies
```

## 🎓 Learning Resources

- Django REST Framework: https://www.django-rest-framework.org/
- RabbitMQ Tutorial: https://www.rabbitmq.com/getstarted.html
- Redis Caching: https://redis.io/docs/manual/client-side-caching/
- JWT Authentication: https://jwt.io/introduction
- pytest Documentation: https://docs.pytest.org/

---

**Happy Coding! 🚀**
