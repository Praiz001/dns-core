# User Service Setup Guide

## Table of Contents
1. [Quick Start (Local Testing)](#quick-start-local-testing)
2. [Full Setup (Production-Ready)](#full-setup-production-ready)
3. [Docker Setup](#docker-setup)
4. [Manual Testing](#manual-testing)

---

## Quick Start (Local Testing)

This setup uses SQLite and in-memory cache for quick testing without external dependencies.

### Prerequisites
- Python 3.11+
- Virtual environment activated

### Steps

1. **Install Dependencies** (already done ✅)
```powershell
pip install -r requirements-windows.txt
```

2. **Create .env file** (already done ✅)
```
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_ENGINE=django.db.backends.sqlite3
```

3. **Run Migrations**
```powershell
cd services\user-service
python manage.py makemigrations
python manage.py migrate
```

4. **Create Superuser**
```powershell
python manage.py createsuperuser
```

5. **Run Server**
```powershell
python manage.py runserver 8001
```

6. **Access API**
- API: http://localhost:8001/api/v1/
- API Docs: http://localhost:8001/api/swagger/
- Admin: http://localhost:8001/admin/

---

## Full Setup (Production-Ready)

This setup uses PostgreSQL, Redis, and RabbitMQ for production deployment.

### Option 1: Install Services Manually on Windows

#### 1. Install PostgreSQL
- Download: https://www.postgresql.org/download/windows/
- Install and create database:
```sql
CREATE DATABASE user_service_db;
CREATE USER postgres WITH PASSWORD 'postgres';
GRANT ALL PRIVILEGES ON DATABASE user_service_db TO postgres;
```

#### 2. Install Redis
- Download: https://github.com/microsoftarchive/redis/releases
- Or use WSL2: `wsl --install` then `sudo apt install redis-server`
- Start Redis: `redis-server`

#### 3. Install RabbitMQ
- Download: https://www.rabbitmq.com/download.html
- Install Erlang first: https://www.erlang.org/downloads
- Start RabbitMQ: `rabbitmq-server start`

#### 4. Install psycopg2 and hiredis
You need Microsoft Visual C++ 14.0+:
- Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
- Then install:
```powershell
pip install psycopg2-binary==2.9.9
pip install hiredis==2.3.2
```

#### 5. Update settings.py
Uncomment PostgreSQL and Redis settings in `user_service/settings.py`

#### 6. Update .env
```
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,localhost

# PostgreSQL
DB_ENGINE=django.db.backends.postgresql
DB_NAME=user_service_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_CACHE_TTL=3600

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VHOST=/

# JWT
JWT_ACCESS_TOKEN_LIFETIME=60
```

---

## Option 2: Docker Setup (Recommended)

Docker provides PostgreSQL, Redis, and RabbitMQ without manual installation.

### Prerequisites
- Docker Desktop for Windows
- Docker Compose

### Steps

1. **Start all services with Docker Compose**
```powershell
cd services\user-service
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- RabbitMQ (port 5672, Management UI: 15672)
- Django User Service (port 8001)

2. **Run migrations inside Docker**
```powershell
docker-compose exec user-service python manage.py migrate
docker-compose exec user-service python manage.py createsuperuser
```

3. **View logs**
```powershell
docker-compose logs -f user-service
```

4. **Stop services**
```powershell
docker-compose down
```

5. **Access Services**
- API: http://localhost:8001/api/v1/
- RabbitMQ Management: http://localhost:15672 (guest/guest)
- PostgreSQL: localhost:5432

---

## Manual Testing

### 1. Test Health Check
```powershell
curl http://localhost:8001/health/
```

### 2. Register User
```powershell
curl -X POST http://localhost:8001/api/v1/register/ `
  -H "Content-Type: application/json" `
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!",
    "first_name": "Test",
    "last_name": "User"
  }'
```

### 3. Login
```powershell
curl -X POST http://localhost:8001/api/v1/auth/login/ `
  -H "Content-Type: application/json" `
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }'
```

Save the `access_token` from response.

### 4. Get Profile (Authenticated)
```powershell
curl http://localhost:8001/api/v1/profile/ `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 5. Update Preferences
```powershell
curl -X PUT http://localhost:8001/api/v1/preferences/ `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" `
  -H "Content-Type: application/json" `
  -d '{
    "email_enabled": true,
    "push_enabled": false,
    "sms_enabled": false
  }'
```

---

## Testing Checklist

Before pushing to production:

- [ ] PostgreSQL is running and accessible
- [ ] Redis is running and accessible
- [ ] RabbitMQ is running and accessible
- [ ] `.env` has production values (DEBUG=False)
- [ ] Database migrations run successfully
- [ ] User registration works
- [ ] User login returns access token
- [ ] Authenticated endpoints work with Bearer token
- [ ] API documentation accessible at /api/swagger/
- [ ] Tests pass: `pytest`
- [ ] No sensitive data in `.env` (add to .gitignore)

---

## Switching Between Local and Production

### For Local Testing (SQLite):
In `settings.py`, keep:
```python
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.sqlite3'),
        'NAME': config('DB_NAME', default=BASE_DIR / 'db.sqlite3'),
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}
```

### For Production (PostgreSQL + Redis):
In `settings.py`, uncomment the PostgreSQL and Redis sections, or use environment variables:

```python
if config('DB_ENGINE', default='django.db.backends.sqlite3') == 'django.db.backends.postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='user_service_db'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default='postgres'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
```

---

## Troubleshooting

### "No module named 'psycopg2'"
- Install Visual C++ Build Tools
- Then: `pip install psycopg2-binary`

### "Connection refused" for PostgreSQL/Redis/RabbitMQ
- Make sure services are running
- Check ports are not blocked by firewall
- Use Docker for easier setup

### "Access token expired"
- Tokens expire after 60 minutes (default)
- Login again to get a new token
- Adjust `JWT_ACCESS_TOKEN_LIFETIME` in .env if needed

---

## Next Steps

1. Test locally with SQLite ✅
2. Set up Docker for full stack testing
3. Configure production environment variables
4. Deploy to cloud (AWS/Azure/GCP)
5. Set up CI/CD pipeline
