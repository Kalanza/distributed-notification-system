# Heroku Deployment Guide

This guide walks you through deploying the Distributed Notification System to Heroku.

## Prerequisites

1. **Heroku Account**: Sign up at https://heroku.com
2. **Heroku CLI**: Install from https://devcenter.heroku.com/articles/heroku-cli
3. **Git**: Ensure git is installed and your project is in a git repository

## Step 1: Install and Login to Heroku CLI

```powershell
# Verify Heroku CLI installation
heroku --version

# Login to Heroku
heroku login
```

## Step 2: Create a Heroku App

```powershell
# Create a new Heroku app (replace 'your-app-name' with your desired name)
heroku create your-notification-system

# Or create with a specific region
heroku create your-notification-system --region us

# The output will show your app URL: https://your-notification-system.herokuapp.com/
```

## Step 3: Add Required Add-ons

```powershell
# Add PostgreSQL database
heroku addons:create heroku-postgresql:mini

# Add Redis for caching and rate limiting
heroku addons:create heroku-redis:mini

# Add CloudAMQP for RabbitMQ message queue
heroku addons:create cloudamqp:lemur

# Verify add-ons were created
heroku addons
```

## Step 4: Set Environment Variables

```powershell
# Required: Email Configuration (Gmail example)
heroku config:set SMTP_USER=your-email@gmail.com
heroku config:set SMTP_PASSWORD=your-app-password
heroku config:set SMTP_FROM_EMAIL=noreply@yourdomain.com

# Optional: Push Notification Configuration (OneSignal)
heroku config:set ONESIGNAL_APP_ID=your-onesignal-app-id
heroku config:set ONESIGNAL_REST_API_KEY=your-onesignal-api-key

# Application Configuration
heroku config:set PYTHONPATH=/app
heroku config:set LOG_LEVEL=INFO
heroku config:set RATE_LIMIT_PER_USER=100
heroku config:set RATE_LIMIT_WINDOW=60

# Generate a secure JWT secret
heroku config:set JWT_SECRET_KEY=$(openssl rand -base64 32)

# Circuit Breaker Configuration
heroku config:set CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
heroku config:set CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60

# View all config vars
heroku config
```

### Getting Gmail App Password

1. Go to your Google Account settings
2. Enable 2-Step Verification
3. Go to Security > 2-Step Verification > App passwords
4. Generate a new app password for "Mail"
5. Use this 16-character password for `SMTP_PASSWORD`

## Step 5: Initialize Git Repository (if not already done)

```powershell
# Initialize git if not already done
git init

# Add all files
git add .

# Commit changes
git commit -m "Initial commit for Heroku deployment"
```

## Step 6: Deploy to Heroku

### Option A: Standard Deployment (Recommended for simplicity)

```powershell
# Add Heroku remote
heroku git:remote -a your-notification-system

# Push to Heroku
git push heroku main

# If your default branch is 'master', use:
# git push heroku master
```

### Option B: Container Deployment (Advanced)

```powershell
# Set stack to container
heroku stack:set container

# Deploy using heroku.yml
git push heroku main
```

## Step 7: Scale Your Application

```powershell
# Scale the web dyno (API Gateway)
heroku ps:scale web=1

# For worker processes (optional, if using background workers)
# heroku ps:scale email-worker=1
# heroku ps:scale push-worker=1
```

## Step 8: Verify Deployment

```powershell
# Open your app in browser
heroku open

# View logs
heroku logs --tail

# Check app health
curl https://your-notification-system.herokuapp.com/health

# Or in PowerShell
Invoke-RestMethod -Uri "https://your-notification-system.herokuapp.com/health"
```

## Step 9: Access API Documentation

Once deployed, access your API documentation at:
- **Swagger UI**: https://your-notification-system.herokuapp.com/docs
- **ReDoc**: https://your-notification-system.herokuapp.com/redoc

## Troubleshooting

### View Logs
```powershell
# View real-time logs
heroku logs --tail

# View last 200 lines
heroku logs -n 200

# Filter by source
heroku logs --source app
```

### Check Dyno Status
```powershell
heroku ps
```

### Restart Application
```powershell
heroku restart
```

### Run Commands
```powershell
# Access bash shell
heroku run bash

# Run Python commands
heroku run python -c "import sys; print(sys.version)"
```

### Database Management
```powershell
# Access PostgreSQL database
heroku pg:psql

# View database info
heroku pg:info

# Create database backup
heroku pg:backups:capture
```

### Redis Management
```powershell
# View Redis info
heroku redis:info

# Access Redis CLI
heroku redis:cli
```

### CloudAMQP Management
```powershell
# Open CloudAMQP dashboard
heroku addons:open cloudamqp
```

## Testing Your Deployment

### 1. Health Check
```powershell
Invoke-RestMethod -Uri "https://your-notification-system.herokuapp.com/health"
```

### 2. Create a User
```powershell
$body = @{
    name = "John Doe"
    email = "john@example.com"
    password = "password123"
    push_token = "test-token"
    preferences = @{
        email = $true
        push = $true
    }
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://your-notification-system.herokuapp.com/api/v1/users/" -Method Post -Body $body -ContentType "application/json"
```

### 3. Send a Notification
```powershell
$notification = @{
    user_id = "YOUR-USER-ID-FROM-ABOVE"
    notification_type = "email"
    template_code = "welcome"
    variables = @{
        name = "John"
        link = "https://example.com"
    }
    priority = 5
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://your-notification-system.herokuapp.com/api/v1/notifications/" -Method Post -Body $notification -ContentType "application/json"
```

## Monitoring and Metrics

### Enable Heroku Metrics (Free)
```powershell
# View metrics dashboard
heroku open --app your-notification-system
# Click on "Metrics" tab
```

### View Application Metrics
```powershell
Invoke-RestMethod -Uri "https://your-notification-system.herokuapp.com/metrics"
```

## Upgrading Your Plan

### Upgrade Database
```powershell
heroku addons:upgrade heroku-postgresql:basic
```

### Upgrade Redis
```powershell
heroku addons:upgrade heroku-redis:premium-0
```

### Upgrade RabbitMQ
```powershell
heroku addons:upgrade cloudamqp:cat
```

## Cost Estimates

### Free Tier (Development)
- **Dynos**: Free (550-1000 hours/month)
- **PostgreSQL**: Mini ($5/month) or Free (limited)
- **Redis**: Mini ($3/month)
- **CloudAMQP**: Lemur (Free - 1M messages/month)
- **Total**: ~$8-10/month (or free with limitations)

### Production Tier
- **Dynos**: Basic ($7/dyno/month)
- **PostgreSQL**: Standard-0 ($50/month)
- **Redis**: Premium-0 ($15/month)
- **CloudAMQP**: Cat ($19/month)
- **Total**: ~$91/month minimum

## Environment-Specific Deployment

### Deploy to Staging
```powershell
# Create staging app
heroku create your-notification-system-staging

# Add same add-ons
heroku addons:create heroku-postgresql:mini --app your-notification-system-staging
heroku addons:create heroku-redis:mini --app your-notification-system-staging
heroku addons:create cloudamqp:lemur --app your-notification-system-staging

# Deploy
git push https://git.heroku.com/your-notification-system-staging.git main
```

### Pipeline Setup (CI/CD)
```powershell
# Create pipeline
heroku pipelines:create your-notification-system

# Add apps to pipeline
heroku pipelines:add your-notification-system --app your-notification-system-staging --stage staging
heroku pipelines:add your-notification-system --app your-notification-system --stage production

# Enable auto-deploy from GitHub
# Go to https://dashboard.heroku.com/apps/your-notification-system/deploy/github
```

## Maintenance Mode

```powershell
# Enable maintenance mode
heroku maintenance:on

# Disable maintenance mode
heroku maintenance:off
```

## Rollback Deployment

```powershell
# View releases
heroku releases

# Rollback to previous version
heroku rollback

# Rollback to specific version
heroku rollback v123
```

## Custom Domain Setup

```powershell
# Add custom domain
heroku domains:add notifications.yourdomain.com

# View DNS targets
heroku domains

# After configuring DNS, add SSL
heroku certs:auto:enable
```

## Continuous Deployment with GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Heroku

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: akhileshns/heroku-deploy@v3.12.12
        with:
          heroku_api_key: ${{secrets.HEROKU_API_KEY}}
          heroku_app_name: "your-notification-system"
          heroku_email: "your-email@example.com"
```

## Important Notes

1. **Free Dyno Sleep**: Free dynos sleep after 30 minutes of inactivity. Upgrade to Basic ($7/month) for 24/7 uptime.

2. **Database Connections**: Free PostgreSQL has a 20-connection limit. Monitor with `heroku pg:info`.

3. **Redis Memory**: Mini Redis has 25MB. Monitor usage with `heroku redis:info`.

4. **Message Queue Limits**: Free CloudAMQP has 1M messages/month limit.

5. **Environment Variables**: Never commit sensitive data. Always use `heroku config:set`.

6. **Logging**: Heroku keeps last 1,500 lines. For permanent logs, use add-ons like Papertrail.

## Next Steps

- Set up monitoring with New Relic or Scout APM
- Configure logging with Papertrail or Loggly
- Set up error tracking with Sentry
- Implement CI/CD with GitHub Actions or Heroku Pipelines
- Configure auto-scaling rules
- Set up database backups schedule

## Support

- **Heroku Documentation**: https://devcenter.heroku.com/
- **Heroku Support**: https://help.heroku.com/
- **Application Logs**: `heroku logs --tail`

## Clean Up (Destroy App)

```powershell
# WARNING: This will permanently delete your app and all data
heroku apps:destroy --app your-notification-system --confirm your-notification-system
```
