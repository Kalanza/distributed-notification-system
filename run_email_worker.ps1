# Run Email Worker Locally (Connected to Heroku Services)
# This script sets up environment variables and runs the email worker

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Email Worker (Local)" -ForegroundColor Cyan
Write-Host "Connected to Heroku Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set Heroku environment variables
$env:CLOUDAMQP_URL = "amqps://mhmzhubl:XfU9YABeDYG1TpnLgItD5XXdxeXDPiwZ@toad.rmq.cloudamqp.com/mhmzhubl"
$env:REDIS_URL = "rediss://:p04f1c2ab94dfa5dc1a53de33f2c0b3ecf63b723eb876e3fd13d2be5d45e8c2d0@ec2-100-25-119-245.compute-1.amazonaws.com:10330"
$env:DATABASE_URL = "postgres://u1k5afvtgvv3q0:pff97e0dfc338bff660bd0942bb4442d31b9760fd36b0c7f965a5d98b4b3e8bf7@c9n6qtf5jru089.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/dapkvp9lp2kh1q"
$env:SMTP_USER = "kalanzavictor@gmail.com"
$env:SMTP_PASSWORD = "vywh dwkh hakd reka"
$env:SMTP_FROM_EMAIL = "kalanzavictor@gmail.com"
$env:SMTP_HOST = "smtp.gmail.com"
$env:SMTP_PORT = "587"
$env:LOG_LEVEL = "INFO"
$env:PYTHONPATH = "C:\Users\USER\Desktop\distributed-notification-system"

Write-Host "✓ Environment variables set" -ForegroundColor Green
Write-Host ""

# Check if in correct directory
if (Test-Path "email_service\main.py") {
    Write-Host "✓ Email service found" -ForegroundColor Green
    Write-Host ""
    Write-Host "Starting email worker..." -ForegroundColor Yellow
    Write-Host "Press Ctrl+C to stop the worker" -ForegroundColor Gray
    Write-Host ""
    
    # Run email worker
    python email_service\main.py
} else {
    Write-Host "✗ Error: email_service/main.py not found" -ForegroundColor Red
    Write-Host "Make sure you're in the project root directory" -ForegroundColor Yellow
}
