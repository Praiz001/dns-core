"""
Django settings for user_service project.
"""

import os
from datetime import timedelta
from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-this-in-production")
DEBUG = config("DEBUG", default=False, cast=bool)

# ALLOWED_HOSTS: Use '*' to allow all, or comma-separated domains
allowed_hosts_str = config("ALLOWED_HOSTS", default="localhost,127.0.0.1")
ALLOWED_HOSTS = ["*"] if allowed_hosts_str == "*" else allowed_hosts_str.split(",")

# Feature toggles / runtime flags
# Explicitly disable test notification publish endpoint in production unless enabled.
ALLOW_TEST_NOTIFICATION_ENDPOINT = config("ALLOW_TEST_NOTIFICATION_ENDPOINT", default=False, cast=bool)

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_yasg",
    "health_check",
    "health_check.db",
    "health_check.cache",
    # Local apps
    "users",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "users.middleware.CorrelationIdMiddleware",
]

ROOT_URLCONF = "user_service.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "user_service.wsgi.application"

# Database
# Automatically switch between SQLite (local) and PostgreSQL (production)
DB_ENGINE = config("DB_ENGINE", default="django.db.backends.sqlite3")

if DB_ENGINE == "django.db.backends.postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="user_service_db"),
            "USER": config("DB_USER", default="postgres"),
            "PASSWORD": config("DB_PASSWORD", default="postgres"),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }
else:
    # SQLite for local development
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Caching - Automatically switch between local memory (local) and Redis (production)
REDIS_HOST = config("REDIS_HOST", default="")
REDIS_URL = config("REDIS_URL", default="")

if REDIS_URL:
    # Redis cache using full URL (e.g., Upstash with TLS)
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": 50,
                    "ssl_cert_reqs": None,  # For Upstash TLS
                },
            },
            "KEY_PREFIX": "user_service",
            "TIMEOUT": config("REDIS_CACHE_TTL", default=3600, cast=int),
        }
    }
elif REDIS_HOST:
    # Redis cache for production (host-based config)
    redis_port = config("REDIS_PORT", default="6379")
    redis_db = config("REDIS_DB", default="0")
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"redis://{REDIS_HOST}:{redis_port}/{redis_db}",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {"max_connections": 50},
            },
            "KEY_PREFIX": "user_service",
            "TIMEOUT": config("REDIS_CACHE_TTL", default=3600, cast=int),
        }
    }
else:
    # Local memory cache for development
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom User Model
AUTH_USER_MODEL = "users.User"

# REST Framework
REST_FRAMEWORK = {
    # Prefer JWT Bearer tokens for API access. Remove Basic/Session to avoid confusion in Swagger
    # and to ensure Authorization: Bearer <token> is the primary auth path.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "users.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "EXCEPTION_HANDLER": "users.exceptions.custom_exception_handler",
}

# JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=config("JWT_ACCESS_TOKEN_LIFETIME", default=60, cast=int)),
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "UPDATE_LAST_LOGIN": True,
}

# Swagger / drf-yasg configuration
SWAGGER_SETTINGS = {
    # Disable session login in Swagger to avoid CSRF and use pure JWT flows
    "USE_SESSION_AUTH": False,
    # Only present Bearer in the Authorize modal
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Format: Bearer <access_token>",
        }
    },
}

# CORS
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="http://localhost:3000").split(",")
CORS_ALLOW_CREDENTIALS = True

# RabbitMQ Configuration
RABBITMQ_CONFIG = {
    "HOST": config("RABBITMQ_HOST", default="localhost"),
    "PORT": config("RABBITMQ_PORT", default=5672, cast=int),
    "USER": config("RABBITMQ_USER", default="guest"),
    "PASSWORD": config("RABBITMQ_PASSWORD", default="guest"),
    "VHOST": config("RABBITMQ_VHOST", default="/"),
    "USE_SSL": config("RABBITMQ_USE_SSL", default=False, cast=bool),
    "QUEUE_PUSH": config("RABBITMQ_QUEUE_PUSH", default="push.queue"),
    "EXCHANGE": config("RABBITMQ_EXCHANGE", default="notifications.direct"),
}

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "json": {
            "()": "users.logging_formatters.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "user_service.log",
            "maxBytes": 1024 * 1024 * 10,  # 10MB
            "backupCount": 5,
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": config("LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "WARNING",  # Only show warnings and errors
            "propagate": False,
        },
        "django.server": {
            "handlers": ["file"],  # Server logs only to file, not console
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "file"],
            "level": "ERROR",  # Only show request errors
            "propagate": False,
        },
        "users": {
            "handlers": ["console", "file"],
            "level": "INFO",  # Changed from DEBUG to INFO
            "propagate": False,
        },
    },
}

# Create logs directory if it doesn't exist
os.makedirs(BASE_DIR / "logs", exist_ok=True)
