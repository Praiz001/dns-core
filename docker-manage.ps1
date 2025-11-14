# DNS Notification System - Docker Management Script
# This script helps manage Docker containers for the DNS notification system

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("up", "down", "build", "rebuild", "logs", "ps", "test", "help")]
    [string]$Action = "help"
)

$Colors = @{
    Green = "`e[92m"
    Red = "`e[91m"
    Yellow = "`e[93m"
    Blue = "`e[94m"
    Reset = "`e[0m"
}

function Write-ColoredOutput {
    param(
        [string]$Message,
        [string]$Color = "Reset"
    )
    Write-Host "$($Colors[$Color])$Message$($Colors.Reset)"
}

function Show-Help {
    Write-ColoredOutput "==============================================================" "Blue"
    Write-ColoredOutput "DNS Notification System - Docker Management" "Yellow"
    Write-ColoredOutput "==============================================================" "Blue"
    Write-Host ""
    Write-ColoredOutput "Available Commands:" "Yellow"
    Write-Host ""
    Write-Host "  up        - Start all services (docker-compose up -d)"
    Write-Host "  down      - Stop all services (docker-compose down)"
    Write-Host "  build     - Build all Docker images"
    Write-Host "  rebuild   - Rebuild and restart all services"
    Write-Host "  logs      - View logs from all services"
    Write-Host "  ps        - Show running containers"
    Write-Host "  test      - Run end-to-end integration tests"
    Write-Host "  help      - Show this help message"
    Write-Host ""
    Write-ColoredOutput "Examples:" "Yellow"
    Write-Host "  .\docker-manage.ps1 up        # Start all services"
    Write-Host "  .\docker-manage.ps1 logs      # View all logs"
    Write-Host "  .\docker-manage.ps1 test      # Run integration tests"
    Write-Host ""
    Write-ColoredOutput "==============================================================" "Blue"
}

function Start-Services {
    Write-ColoredOutput "`n🚀 Starting DNS Notification System services..." "Blue"
    Write-Host ""
    
    # Check if .env files exist
    $envFiles = @(
        "services\api-gateway\.env",
        "services\email-service\.env",
        "services\push-service\.env",
        "services\template-service\.env"
    )
    
    $missingEnv = @()
    foreach ($envFile in $envFiles) {
        if (-not (Test-Path $envFile)) {
            $missingEnv += $envFile
        }
    }
    
    if ($missingEnv.Count -gt 0) {
        Write-ColoredOutput "⚠️  Warning: Missing .env files:" "Yellow"
        foreach ($file in $missingEnv) {
            Write-Host "   - $file (using docker-compose environment instead)"
        }
        Write-Host ""
    }
    
    docker-compose up -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColoredOutput "`n✅ Services started successfully!" "Green"
        Write-Host ""
        Write-ColoredOutput "Service URLs:" "Yellow"
        Write-Host "  API Gateway:      http://localhost:3000"
        Write-Host "  User Service:     http://localhost:8001"
        Write-Host "  Template Service: http://localhost:8002"
        Write-Host "  Email Service:    http://localhost:8003"
        Write-Host "  Push Service:     http://localhost:8005"
        Write-Host ""
        Write-Host "  PostgreSQL:       localhost:5432"
        Write-Host "  Redis:            localhost:6379"
        Write-Host "  RabbitMQ:         localhost:5672 (Management: http://localhost:15672)"
        Write-Host ""
        Write-ColoredOutput "Waiting for services to be ready..." "Blue"
        Start-Sleep -Seconds 10
        docker-compose ps
    } else {
        Write-ColoredOutput "`n❌ Failed to start services!" "Red"
        exit 1
    }
}

function Stop-Services {
    Write-ColoredOutput "`n🛑 Stopping DNS Notification System services..." "Blue"
    docker-compose down
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColoredOutput "`n✅ Services stopped successfully!" "Green"
    } else {
        Write-ColoredOutput "`n❌ Failed to stop services!" "Red"
        exit 1
    }
}

function Build-Services {
    Write-ColoredOutput "`n🔨 Building Docker images..." "Blue"
    docker-compose build --no-cache
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColoredOutput "`n✅ Build completed successfully!" "Green"
    } else {
        Write-ColoredOutput "`n❌ Build failed!" "Red"
        exit 1
    }
}

function Rebuild-Services {
    Write-ColoredOutput "`n🔄 Rebuilding and restarting services..." "Blue"
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColoredOutput "`n✅ Services rebuilt and started successfully!" "Green"
        Start-Sleep -Seconds 10
        docker-compose ps
    } else {
        Write-ColoredOutput "`n❌ Rebuild failed!" "Red"
        exit 1
    }
}

function Show-Logs {
    Write-ColoredOutput "`n📋 Viewing service logs (Ctrl+C to exit)..." "Blue"
    Write-Host ""
    docker-compose logs -f
}

function Show-Ps {
    Write-ColoredOutput "`n📊 Running containers:" "Blue"
    Write-Host ""
    docker-compose ps
}

function Run-Tests {
    Write-ColoredOutput "`n🧪 Running end-to-end integration tests..." "Blue"
    Write-Host ""
    
    # Check if services are running
    $running = docker-compose ps --services --filter "status=running" | Measure-Object -Line
    if ($running.Lines -lt 5) {
        Write-ColoredOutput "⚠️  Warning: Not all services are running. Starting services first..." "Yellow"
        Start-Services
        Start-Sleep -Seconds 15
    }
    
    # Install required packages for testing
    Write-ColoredOutput "Installing test dependencies..." "Blue"
    pip install httpx asyncio --quiet
    
    # Run integration tests
    Write-Host ""
    python test_e2e_integration.py
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColoredOutput "`n✅ Integration tests completed!" "Green"
    } else {
        Write-ColoredOutput "`n⚠️  Some tests may have failed. Check output above." "Yellow"
    }
}

# Main script execution
switch ($Action) {
    "up" { Start-Services }
    "down" { Stop-Services }
    "build" { Build-Services }
    "rebuild" { Rebuild-Services }
    "logs" { Show-Logs }
    "ps" { Show-Ps }
    "test" { Run-Tests }
    "help" { Show-Help }
    default { Show-Help }
}
