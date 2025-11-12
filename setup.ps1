# Quick setup script for Windows (PowerShell)

Write-Host "[*] Setting up Distributed Notification System..." -ForegroundColor Green

# Check if Docker is installed
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check if Docker Compose is available
if (!(Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Docker Compose is not installed. Please install Docker Compose first." -ForegroundColor Red
    exit 1
}

# Create .env file if it doesn't exist
if (!(Test-Path .env)) {
    Write-Host "[INFO] Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "[WARN] Please edit .env file with your configuration before starting services" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Press Enter to open .env file for editing..." -ForegroundColor Cyan
    Read-Host
    notepad .env
    Write-Host ""
    Write-Host "After saving your changes, press Enter to continue..." -ForegroundColor Cyan
    Read-Host
}

# Pull required images
Write-Host "[INFO] Pulling Docker images..." -ForegroundColor Cyan
docker-compose pull

# Build services
Write-Host "[INFO] Building services..." -ForegroundColor Cyan
docker-compose build

# Start services
Write-Host "[INFO] Starting services..." -ForegroundColor Cyan
docker-compose up -d

# Wait for services to be ready
Write-Host "[INFO] Waiting for services to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# Check health
Write-Host "[INFO] Checking service health..." -ForegroundColor Cyan
$services = @{
    "http://localhost:8000/health" = "API Gateway"
    "http://localhost:8003/health" = "User Service"
    "http://localhost:8004/health" = "Template Service"
    "http://localhost:8001/health" = "Email Service"
    "http://localhost:8002/health" = "Push Service"
}

foreach ($url in $services.Keys) {
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "[OK] $($services[$url]) is running" -ForegroundColor Green
        }
    } catch {
        Write-Host "[FAIL] $($services[$url]) is not responding" -ForegroundColor Red
    }
}

# Create test user
Write-Host ""
Write-Host "[INFO] Creating test user..." -ForegroundColor Cyan
$userBody = @{
    username = "testuser"
    email = "test@example.com"
    phone_number = "+1234567890"
    password = "testpass123"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8003/users" `
        -Method Post `
        -Body $userBody `
        -ContentType "application/json"
    Write-Host "User created: $($response | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "Note: User might already exist" -ForegroundColor Yellow
}

# Create test template
Write-Host ""
Write-Host "[INFO] Creating email template..." -ForegroundColor Cyan
$templateBody = @{
    template_id = "welcome_email"
    name = "Welcome Email"
    channel = "email"
    subject = "Welcome {{name}}!"
    body_text = "Hello {{name}}, welcome to our platform!"
    body_html = "<h1>Hello {{name}}</h1><p>Welcome to our platform!</p>"
    variables = @("name")
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8004/templates" `
        -Method Post `
        -Body $templateBody `
        -ContentType "application/json"
    Write-Host "Template created: $($response | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "Note: Template might already exist" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[SUCCESS] Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "[NEXT STEPS]" -ForegroundColor Cyan
Write-Host "  1. If needed, edit .env with your SMTP and FCM credentials"
Write-Host "  2. Restart services if you changed .env: docker-compose restart"
Write-Host "  3. View RabbitMQ: http://localhost:15672 (guest/guest)"
Write-Host "  4. View API docs: http://localhost:8000/docs"
Write-Host ""
Write-Host "[DOCUMENTATION]" -ForegroundColor Cyan
Write-Host "  - README.md - Overview and features"
Write-Host ""
