# User Service Deployment Guide

## 📋 Pre-Deployment Checklist

### 1. Code Quality
- [ ] All tests passing (`pytest`)
- [ ] Code linted (`flake8`, `black`, `isort`)
- [ ] No security vulnerabilities
- [ ] Code reviewed and approved
- [ ] Documentation updated

### 2. Configuration
- [ ] Environment variables configured
- [ ] Database credentials secured
- [ ] Secret key generated and secured
- [ ] CORS settings configured
- [ ] Allowed hosts configured
- [ ] Debug mode disabled

### 3. Infrastructure
- [ ] PostgreSQL database provisioned
- [ ] Redis cache provisioned
- [ ] RabbitMQ message queue provisioned
- [ ] Load balancer configured
- [ ] SSL/TLS certificates installed
- [ ] Monitoring setup
- [ ] Logging infrastructure ready
- [ ] Backup strategy in place

## 🚀 Deployment Methods

### Method 1: Docker Compose (Simple)

Best for: Small deployments, single server

```bash
# On your server
git clone <repository>
cd services/user-service

# Configure environment
cp .env.example .env
nano .env  # Edit with production values

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose exec user_service python manage.py migrate

# Collect static files
docker-compose exec user_service python manage.py collectstatic --noinput

# Create superuser
docker-compose exec user_service python manage.py createsuperuser
```

### Method 2: Kubernetes (Production)

Best for: Large scale, high availability

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
  labels:
    app: user-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: user-service
  template:
    metadata:
      labels:
        app: user-service
    spec:
      containers:
      - name: user-service
        image: ghcr.io/your-org/user-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: DB_HOST
          value: postgres-service
        - name: REDIS_HOST
          value: redis-service
        - name: RABBITMQ_HOST
          value: rabbitmq-service
        envFrom:
        - secretRef:
            name: user-service-secrets
        livenessProbe:
          httpGet:
            path: /api/v1/health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health/
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Check status
kubectl get pods -l app=user-service
kubectl logs -f deployment/user-service

# Scale replicas
kubectl scale deployment user-service --replicas=5
```

### Method 3: Cloud Platforms

#### AWS Elastic Beanstalk

```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.11 user-service

# Create environment
eb create user-service-prod

# Deploy
eb deploy

# Configure environment variables
eb setenv SECRET_KEY=xxx DB_HOST=xxx
```

#### Google Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/user-service

# Deploy
gcloud run deploy user-service \
  --image gcr.io/PROJECT_ID/user-service \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### Azure Container Instances

```bash
# Create resource group
az group create --name user-service-rg --location eastus

# Deploy container
az container create \
  --resource-group user-service-rg \
  --name user-service \
  --image your-registry/user-service:latest \
  --dns-name-label user-service \
  --ports 8000
```

## 🔧 Production Configuration

### Docker Compose Production

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  user_service:
    image: ghcr.io/your-org/user-service:${VERSION:-latest}
    restart: always
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
    env_file:
      - .env.production
    depends_on:
      - db
      - redis
      - rabbitmq
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  db:
    image: postgres:15-alpine
    restart: always
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M

  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    restart: always
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1G

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
      - static_volume:/app/staticfiles
    depends_on:
      - user_service

volumes:
  postgres_data:
  redis_data:
  rabbitmq_data:
  static_volume:
```

### Feature Flags

- ALLOW_TEST_NOTIFICATION_ENDPOINT: Controls whether POST /api/v1/notifications/test/ is available. Default is False (disabled) in production. Set to True temporarily only for troubleshooting.

### Environment Hostnames when using Docker Compose

When using docker-compose, prefer service names instead of localhost:

- DB_HOST=db
- REDIS_HOST=redis
- RABBITMQ_HOST=rabbitmq

If you use managed cloud services, set those hosts accordingly and, for CloudAMQP/Upstash, enable TLS and use the proper URL/flags.

### Nginx Configuration

```nginx
# nginx.conf
upstream user_service {
    least_conn;
    server user_service:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    client_max_body_size 10M;

    location / {
        proxy_pass http://user_service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## 🔒 Security Hardening

### 1. Environment Variables

```env
# .env.production
SECRET_KEY=<generate-with-django-secret-key-generator>
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Database (use managed service)
DB_NAME=user_service_prod
DB_USER=user_service_app
DB_PASSWORD=<strong-random-password>
DB_HOST=<managed-postgres-host>
DB_PORT=5432

# Redis (use managed service)
REDIS_HOST=<managed-redis-host>
REDIS_PORT=6379
REDIS_PASSWORD=<strong-random-password>

# RabbitMQ (use managed service)
RABBITMQ_HOST=<managed-rabbitmq-host>
RABBITMQ_PORT=5672
RABBITMQ_USER=user_service
RABBITMQ_PASSWORD=<strong-random-password>

# JWT
JWT_ACCESS_TOKEN_LIFETIME=15
JWT_REFRESH_TOKEN_LIFETIME=1440

# CORS
CORS_ALLOWED_ORIGINS=https://your-frontend.com

# SSL
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### 2. Django Security Settings

Add to `settings.py` for production:

```python
# Security
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

## 📊 Monitoring & Logging

### 1. Application Monitoring

```python
# Install Sentry
pip install sentry-sdk

# Add to settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True
)
```

### 2. Log Aggregation

Use a centralized logging solution:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Datadog**
- **New Relic**
- **CloudWatch** (AWS)
- **Stackdriver** (GCP)

### 3. Health Monitoring

```bash
# Set up monitoring endpoint checks
curl -f https://your-domain.com/api/v1/health/ || exit 1

# Use tools like:
# - Uptime Robot
# - Pingdom
# - StatusCake
# - AWS CloudWatch
```

## 🔄 CI/CD Pipeline

The GitHub Actions workflow is already configured. To use it:

1. **Push to main branch** triggers deployment
2. **Secrets required** in GitHub:
   - `DOCKER_USERNAME`
   - `DOCKER_PASSWORD`
   - `PRODUCTION_SERVER_SSH_KEY`
   - `PRODUCTION_SERVER_HOST`

## 📦 Database Migrations

```bash
# Before deployment, test migrations on staging
python manage.py migrate --plan

# During deployment
docker-compose exec user_service python manage.py migrate --noinput

# Rollback if needed
docker-compose exec user_service python manage.py migrate users 0001_initial
```

## 🔧 Maintenance

### Backup Strategy

```bash
# Database backup (daily)
docker-compose exec db pg_dump -U postgres user_service_db > backup_$(date +%Y%m%d).sql

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T db pg_dump -U postgres user_service_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete
```

### Database Restore

```bash
# Restore from backup
gunzip < backup.sql.gz | docker-compose exec -T db psql -U postgres user_service_db
```

### Scaling

```bash
# Horizontal scaling with Docker Compose
docker-compose up -d --scale user_service=3

# Kubernetes scaling
kubectl scale deployment user-service --replicas=5

# Auto-scaling with Kubernetes
kubectl autoscale deployment user-service --min=3 --max=10 --cpu-percent=70
```

## 🚨 Rollback Procedure

```bash
# Docker rollback
docker-compose down
git checkout previous-stable-tag
docker-compose up -d

# Kubernetes rollback
kubectl rollout undo deployment/user-service
kubectl rollout status deployment/user-service

# Verify rollback
kubectl get pods -l app=user-service
curl https://your-domain.com/api/v1/health/
```

## 📈 Performance Optimization

1. **Database Connection Pooling**: Configured in settings
2. **Redis Caching**: User preferences cached
3. **CDN for Static Files**: Use CloudFront, CloudFlare, or similar
4. **Database Indexes**: Already configured on User model
5. **Gunicorn Workers**: Set to CPU cores * 2 + 1
6. **Query Optimization**: Use select_related and prefetch_related

## 📞 Incident Response

1. **Check service health**: `/api/v1/health/`
2. **Review logs**: `docker-compose logs -f`
3. **Check resource usage**: `docker stats`
4. **Database connections**: `SELECT count(*) FROM pg_stat_activity;`
5. **Redis memory**: `docker-compose exec redis redis-cli INFO memory`
6. **RabbitMQ queues**: Check management UI

## ✅ Post-Deployment Checklist

- [ ] Service is responding to requests
- [ ] Health check endpoint returns 200
- [ ] Database migrations applied
- [ ] Static files collected and served
- [ ] SSL certificate valid
- [ ] Monitoring alerts configured
- [ ] Backup jobs scheduled
- [ ] Load balancer health checks passing
- [ ] API documentation accessible
- [ ] Logs being collected
- [ ] Team notified of deployment

## 🎓 Best Practices

1. **Blue-Green Deployment**: Minimize downtime
2. **Canary Releases**: Roll out to subset of users first
3. **Database Migrations**: Test on staging first
4. **Environment Parity**: Keep dev/staging/prod similar
5. **Secrets Management**: Use vault or cloud secrets manager
6. **Monitoring**: Set up alerts for errors and performance
7. **Documentation**: Keep runbooks updated
8. **Disaster Recovery**: Test restore procedures regularly

---

**Need help? Contact the DevOps team or check the main README.md**
