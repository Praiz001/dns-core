# User Service Quick Start

Write-Host "🚀 Starting User Service Setup..." -ForegroundColor Green

# Check if Docker is installed
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker is not installed. Please install Docker first." -ForegroundColor Red
    exit 1
}

# Check if Docker Compose is installed
if (!(Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker Compose is not installed. Please install Docker Compose first." -ForegroundColor Red
    exit 1
}

# Navigate to user-service directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Create .env from .env.example if it doesn't exist
if (!(Test-Path .env)) {
    Write-Host "📝 Creating .env file from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "✅ .env file created. Please review and update if needed." -ForegroundColor Green
}

# Start Docker containers
Write-Host "🐳 Starting Docker containers..." -ForegroundColor Yellow
docker-compose up -d

# Wait for services to be healthy
Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Run migrations
Write-Host "🔧 Running database migrations..." -ForegroundColor Yellow
docker-compose exec -T user_service python manage.py migrate

# Create superuser (optional)
Write-Host ""
$createSuperuser = Read-Host "Would you like to create a superuser? (y/n)"
if ($createSuperuser -eq "y") {
    docker-compose exec user_service python manage.py createsuperuser
}

Write-Host ""
Write-Host "✅ User Service is ready!" -ForegroundColor Green
Write-Host ""
Write-Host "📚 Available endpoints:" -ForegroundColor Cyan
Write-Host "  - API: http://localhost:8000/api/v1/" -ForegroundColor White
Write-Host "  - Swagger UI: http://localhost:8000/swagger/" -ForegroundColor White
Write-Host "  - ReDoc: http://localhost:8000/redoc/" -ForegroundColor White
Write-Host "  - Admin: http://localhost:8000/admin/" -ForegroundColor White
Write-Host "  - Health: http://localhost:8000/api/v1/health/" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Management URLs:" -ForegroundColor Cyan
Write-Host "  - RabbitMQ Management: http://localhost:15672/ (guest/guest)" -ForegroundColor White
Write-Host ""
Write-Host "📋 Useful commands:" -ForegroundColor Cyan
Write-Host "  - View logs: docker-compose logs -f user_service" -ForegroundColor White
Write-Host "  - Stop services: docker-compose down" -ForegroundColor White
Write-Host "  - Run tests: docker-compose exec user_service pytest" -ForegroundColor White
Write-Host "  - Shell access: docker-compose exec user_service python manage.py shell" -ForegroundColor White
Write-Host ""
