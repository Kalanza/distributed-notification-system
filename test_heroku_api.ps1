# Test Script for Heroku Deployed Notification System
# This script tests your deployed API endpoints

$baseUrl = "https://distributed-notif-system-3037-a8c646106fe0.herokuapp.com"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Testing Deployed Notification System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Health Check
Write-Host "[1/4] Testing Health Endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
    Write-Host "✓ Health Status: $($health.data.status)" -ForegroundColor Green
    Write-Host "  - RabbitMQ: $($health.data.dependencies.rabbitmq)" -ForegroundColor Gray
    Write-Host "  - Redis: $($health.data.dependencies.redis)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Health check failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test 2: Create a User
Write-Host "[2/4] Creating Test User..." -ForegroundColor Yellow
$userBody = @{
    name = "Test User"
    email = "kalanzavictor@gmail.com"
    password = "TestPassword123!"
    push_token = "test-push-token-12345"
    preferences = @{
        email = $true
        push = $true
    }
} | ConvertTo-Json

try {
    $userResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/users/" -Method Post -Body $userBody -ContentType "application/json"
    $userId = $userResponse.data.user_id
    Write-Host "✓ User created successfully!" -ForegroundColor Green
    Write-Host "  User ID: $userId" -ForegroundColor Gray
    Write-Host "  Email: $($userResponse.data.email)" -ForegroundColor Gray
} catch {
    Write-Host "✗ User creation failed: $_" -ForegroundColor Red
    Write-Host "  This might be OK if user already exists" -ForegroundColor Yellow
    # Use a default user ID for testing
    $userId = "00000000-0000-0000-0000-000000000001"
}

Write-Host ""

# Test 3: Send Email Notification
Write-Host "[3/4] Sending Email Notification..." -ForegroundColor Yellow
$notificationBody = @{
    user_id = $userId
    notification_type = "email"
    template_code = "welcome"
    variables = @{
        name = "Test User"
        link = "https://example.com/welcome"
        meta = "This is a test email from Heroku"
    }
    priority = 5
    metadata = @{
        source = "test_script"
        environment = "heroku"
    }
} | ConvertTo-Json

try {
    $notifResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/notifications/" -Method Post -Body $notificationBody -ContentType "application/json"
    Write-Host "✓ Notification queued successfully!" -ForegroundColor Green
    Write-Host "  Notification ID: $($notifResponse.data.notification_id)" -ForegroundColor Gray
    Write-Host "  Request ID: $($notifResponse.data.request_id)" -ForegroundColor Gray
    Write-Host "  Status: $($notifResponse.data.status)" -ForegroundColor Gray
    Write-Host "  Remaining requests: $($notifResponse.data.remaining_requests)" -ForegroundColor Gray
    
    $notificationId = $notifResponse.data.notification_id
} catch {
    Write-Host "✗ Notification sending failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test 4: Check Notification Status
Write-Host "[4/4] Checking Notification Status..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
try {
    $statusResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/notifications/$notificationId/status" -Method Get
    Write-Host "✓ Status retrieved successfully!" -ForegroundColor Green
    Write-Host "  Status: $($statusResponse.data.status)" -ForegroundColor Gray
    Write-Host "  Timestamp: $($statusResponse.data.timestamp)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Status check failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Testing Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Check your email (kalanzavictor@gmail.com) for the test notification!" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. View API docs: https://distributed-notif-system-3037-a8c646106fe0.herokuapp.com/docs" -ForegroundColor Gray
Write-Host "  2. Monitor logs: heroku logs --tail --app distributed-notif-system-3037" -ForegroundColor Gray
Write-Host "  3. Check metrics: https://distributed-notif-system-3037-a8c646106fe0.herokuapp.com/metrics" -ForegroundColor Gray
Write-Host ""
