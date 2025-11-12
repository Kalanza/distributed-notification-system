# Heroku Deployment Script for Distributed Notification System
# Run this script to automate Heroku deployment

param(
    [Parameter(Mandatory=$true)]
    [string]$AppName,
    
    [Parameter(Mandatory=$true)]
    [string]$SmtpUser,
    
    [Parameter(Mandatory=$true)]
    [string]$SmtpPassword,
    
    [Parameter(Mandatory=$true)]
    [string]$SmtpFromEmail,
    
    [Parameter(Mandatory=$false)]
    [string]$OneSignalAppId = "",
    
    [Parameter(Mandatory=$false)]
    [string]$OneSignalApiKey = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Heroku Deployment Script" -ForegroundColor Cyan
Write-Host "Distributed Notification System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Heroku CLI is installed
Write-Host "[1/10] Checking Heroku CLI installation..." -ForegroundColor Yellow
try {
    $herokuVersion = heroku --version
    Write-Host "✓ Heroku CLI found: $herokuVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Heroku CLI not found. Please install it from https://devcenter.heroku.com/articles/heroku-cli" -ForegroundColor Red
    exit 1
}

# Check if logged in to Heroku
Write-Host ""
Write-Host "[2/10] Checking Heroku authentication..." -ForegroundColor Yellow
try {
    $auth = heroku auth:whoami 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Logged in as: $auth" -ForegroundColor Green
    } else {
        Write-Host "✗ Not logged in to Heroku. Running heroku login..." -ForegroundColor Yellow
        heroku login
    }
} catch {
    Write-Host "✗ Please run 'heroku login' first" -ForegroundColor Red
    exit 1
}

# Create Heroku app
Write-Host ""
Write-Host "[3/10] Creating Heroku app: $AppName..." -ForegroundColor Yellow
$createOutput = heroku create $AppName --region $Region 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ App created successfully" -ForegroundColor Green
} else {
    if ($createOutput -match "already taken") {
        Write-Host "⚠ App name already exists. Using existing app..." -ForegroundColor Yellow
        heroku git:remote -a $AppName
    } else {
        Write-Host "✗ Failed to create app: $createOutput" -ForegroundColor Red
        exit 1
    }
}

# Add PostgreSQL
Write-Host ""
Write-Host "[4/10] Adding PostgreSQL database..." -ForegroundColor Yellow
heroku addons:create heroku-postgresql:mini --app $AppName 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ PostgreSQL added" -ForegroundColor Green
} else {
    Write-Host "⚠ PostgreSQL may already exist or failed to add" -ForegroundColor Yellow
}

# Add Redis
Write-Host ""
Write-Host "[5/10] Adding Redis cache..." -ForegroundColor Yellow
heroku addons:create heroku-redis:mini --app $AppName 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Redis added" -ForegroundColor Green
} else {
    Write-Host "⚠ Redis may already exist or failed to add" -ForegroundColor Yellow
}

# Add CloudAMQP
Write-Host ""
Write-Host "[6/10] Adding CloudAMQP (RabbitMQ)..." -ForegroundColor Yellow
heroku addons:create cloudamqp:lemur --app $AppName 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ CloudAMQP added" -ForegroundColor Green
} else {
    Write-Host "⚠ CloudAMQP may already exist or failed to add" -ForegroundColor Yellow
}

# Wait for add-ons to be ready
Write-Host ""
Write-Host "[7/10] Waiting for add-ons to provision (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30
Write-Host "✓ Add-ons should be ready" -ForegroundColor Green

# Set environment variables
Write-Host ""
Write-Host "[8/10] Setting environment variables..." -ForegroundColor Yellow

$configVars = @{
    "PYTHONPATH" = "/app"
    "LOG_LEVEL" = "INFO"
    "SMTP_USER" = $SmtpUser
    "SMTP_PASSWORD" = $SmtpPassword
    "SMTP_FROM_EMAIL" = $SmtpFromEmail
    "SMTP_HOST" = "smtp.gmail.com"
    "SMTP_PORT" = "587"
    "RATE_LIMIT_PER_USER" = "100"
    "RATE_LIMIT_WINDOW" = "60"
    "CIRCUIT_BREAKER_FAILURE_THRESHOLD" = "5"
    "CIRCUIT_BREAKER_RECOVERY_TIMEOUT" = "60"
}

# Add OneSignal if provided
if ($OneSignalAppId -and $OneSignalApiKey) {
    $configVars["ONESIGNAL_APP_ID"] = $OneSignalAppId
    $configVars["ONESIGNAL_REST_API_KEY"] = $OneSignalApiKey
    Write-Host "  ✓ OneSignal credentials included" -ForegroundColor Green
}

# Generate JWT secret
$jwtSecret = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
$configVars["JWT_SECRET_KEY"] = $jwtSecret

foreach ($key in $configVars.Keys) {
    $value = $configVars[$key]
    heroku config:set "${key}=${value}" --app $AppName 2>&1 | Out-Null
}

Write-Host "✓ Environment variables set" -ForegroundColor Green

# Check if git repository exists
Write-Host ""
Write-Host "[9/10] Preparing Git repository..." -ForegroundColor Yellow
if (-not (Test-Path ".git")) {
    git init
    git add .
    git commit -m "Initial commit for Heroku deployment"
    Write-Host "✓ Git repository initialized" -ForegroundColor Green
} else {
    Write-Host "✓ Git repository exists" -ForegroundColor Green
}

# Add Heroku remote if not exists
$remotes = git remote -v
if ($remotes -notmatch "heroku") {
    heroku git:remote -a $AppName
    Write-Host "✓ Heroku remote added" -ForegroundColor Green
}

# Deploy to Heroku
Write-Host ""
Write-Host "[10/10] Deploying to Heroku..." -ForegroundColor Yellow
Write-Host "This may take several minutes..." -ForegroundColor Cyan
Write-Host ""

# Get current branch
$currentBranch = git rev-parse --abbrev-ref HEAD

# Push to Heroku
git push heroku ${currentBranch}:main --force

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✓ DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your app is deployed at:" -ForegroundColor Cyan
    Write-Host "https://$AppName.herokuapp.com" -ForegroundColor White
    Write-Host ""
    Write-Host "API Documentation:" -ForegroundColor Cyan
    Write-Host "https://$AppName.herokuapp.com/docs" -ForegroundColor White
    Write-Host ""
    Write-Host "Health Check:" -ForegroundColor Cyan
    Write-Host "https://$AppName.herokuapp.com/health" -ForegroundColor White
    Write-Host ""
    Write-Host "Useful Commands:" -ForegroundColor Cyan
    Write-Host "  View logs:      heroku logs --tail --app $AppName" -ForegroundColor Yellow
    Write-Host "  Open app:       heroku open --app $AppName" -ForegroundColor Yellow
    Write-Host "  App info:       heroku apps:info --app $AppName" -ForegroundColor Yellow
    Write-Host "  Scale dynos:    heroku ps:scale web=1 --app $AppName" -ForegroundColor Yellow
    Write-Host ""
    
    # Open the app
    Write-Host "Opening app in browser..." -ForegroundColor Cyan
    Start-Sleep -Seconds 2
    heroku open --app $AppName
    
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "✗ DEPLOYMENT FAILED" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check the logs for errors:" -ForegroundColor Yellow
    Write-Host "heroku logs --tail --app $AppName" -ForegroundColor White
    Write-Host ""
    exit 1
}
