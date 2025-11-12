.PHONY: help install migrate test lint format run docker-up docker-down docker-logs clean

help:
	@echo "User Service - Available Commands"
	@echo "=================================="
	@echo "install      - Install Python dependencies"
	@echo "migrate      - Run database migrations"
	@echo "test         - Run tests with coverage"
	@echo "lint         - Run linting checks"
	@echo "format       - Format code with black and isort"
	@echo "run          - Run development server"
	@echo "consumer     - Run RabbitMQ consumer"
	@echo "docker-up    - Start Docker containers"
	@echo "docker-down  - Stop Docker containers"
	@echo "docker-logs  - View Docker logs"
	@echo "docker-test  - Run tests in Docker"
	@echo "clean        - Remove Python cache files"

install:
	pip install -r requirements.txt

migrate:
	python manage.py migrate

test:
	pytest --cov --cov-report=html --cov-report=term

lint:
	flake8 .
	black --check .
	isort --check-only .

format:
	black .
	isort .

run:
	python manage.py runserver

consumer:
	python manage.py consume_rabbitmq

docker-up:
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 10
	docker-compose exec user_service python manage.py migrate
	@echo "Services are ready!"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-test:
	docker-compose exec user_service pytest

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
