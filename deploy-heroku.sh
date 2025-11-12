#!/bin/bash

# Heroku Deployment Script for Distributed Notification System
# Usage: ./deploy-heroku.sh <app-name> <smtp-user> <smtp-password> <smtp-from-email> [onesignal-app-id] [onesignal-api-key]

set -e

APP_NAME=$1
SMTP_USER=$2
SMTP_PASSWORD=$3
SMTP_FROM_EMAIL=$4
ONESIGNAL_APP_ID=${5:-""}
ONESIGNAL_API_KEY=${6:-""}
REGION=${7:-"us"}

if [ -z "$APP_NAME" ] || [ -z "$SMTP_USER" ] || [ -z "$SMTP_PASSWORD" ] || [ -z "$SMTP_FROM_EMAIL" ]; then
    echo "Usage: $0 <app-name> <smtp-user> <smtp-password> <smtp-from-email> [onesignal-app-id] [onesignal-api-key] [region]"
    echo ""
    echo "Example:"
    echo "  $0 my-notification-app user@gmail.com 'app-password' noreply@example.com"
    exit 1
fi

echo "========================================"
echo "Heroku Deployment Script"
echo "Distributed Notification System"
echo "========================================"
echo ""

# Check Heroku CLI
echo "[1/10] Checking Heroku CLI installation..."
if ! command -v heroku &> /dev/null; then
    echo "✗ Heroku CLI not found. Install from https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi
echo "✓ Heroku CLI found"

# Check authentication
echo ""
echo "[2/10] Checking Heroku authentication..."
if ! heroku auth:whoami &> /dev/null; then
    echo "✗ Not logged in. Running heroku login..."
    heroku login
fi
echo "✓ Authenticated"

# Create app
echo ""
echo "[3/10] Creating Heroku app: $APP_NAME..."
if heroku create $APP_NAME --region $REGION 2>&1 | grep -q "already taken"; then
    echo "⚠ App exists. Using existing app..."
    heroku git:remote -a $APP_NAME
else
    echo "✓ App created"
fi

# Add PostgreSQL
echo ""
echo "[4/10] Adding PostgreSQL..."
heroku addons:create heroku-postgresql:mini --app $APP_NAME || echo "⚠ PostgreSQL may already exist"

# Add Redis
echo ""
echo "[5/10] Adding Redis..."
heroku addons:create heroku-redis:mini --app $APP_NAME || echo "⚠ Redis may already exist"

# Add CloudAMQP
echo ""
echo "[6/10] Adding CloudAMQP..."
heroku addons:create cloudamqp:lemur --app $APP_NAME || echo "⚠ CloudAMQP may already exist"

# Wait for provisioning
echo ""
echo "[7/10] Waiting for add-ons to provision..."
sleep 30
echo "✓ Add-ons ready"

# Set config vars
echo ""
echo "[8/10] Setting environment variables..."
JWT_SECRET=$(openssl rand -base64 32)

heroku config:set \
    PYTHONPATH=/app \
    LOG_LEVEL=INFO \
    SMTP_USER="$SMTP_USER" \
    SMTP_PASSWORD="$SMTP_PASSWORD" \
    SMTP_FROM_EMAIL="$SMTP_FROM_EMAIL" \
    SMTP_HOST=smtp.gmail.com \
    SMTP_PORT=587 \
    RATE_LIMIT_PER_USER=100 \
    RATE_LIMIT_WINDOW=60 \
    CIRCUIT_BREAKER_FAILURE_THRESHOLD=5 \
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60 \
    JWT_SECRET_KEY="$JWT_SECRET" \
    --app $APP_NAME

if [ ! -z "$ONESIGNAL_APP_ID" ] && [ ! -z "$ONESIGNAL_API_KEY" ]; then
    heroku config:set \
        ONESIGNAL_APP_ID="$ONESIGNAL_APP_ID" \
        ONESIGNAL_REST_API_KEY="$ONESIGNAL_API_KEY" \
        --app $APP_NAME
    echo "  ✓ OneSignal credentials included"
fi

echo "✓ Environment variables set"

# Git setup
echo ""
echo "[9/10] Preparing Git repository..."
if [ ! -d ".git" ]; then
    git init
    git add .
    git commit -m "Initial commit for Heroku deployment"
    echo "✓ Git repository initialized"
else
    echo "✓ Git repository exists"
fi

if ! git remote | grep -q "heroku"; then
    heroku git:remote -a $APP_NAME
    echo "✓ Heroku remote added"
fi

# Deploy
echo ""
echo "[10/10] Deploying to Heroku..."
echo "This may take several minutes..."
echo ""

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
git push heroku $CURRENT_BRANCH:main --force

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "✓ DEPLOYMENT SUCCESSFUL!"
    echo "========================================"
    echo ""
    echo "Your app is deployed at:"
    echo "https://$APP_NAME.herokuapp.com"
    echo ""
    echo "API Documentation:"
    echo "https://$APP_NAME.herokuapp.com/docs"
    echo ""
    echo "Health Check:"
    echo "https://$APP_NAME.herokuapp.com/health"
    echo ""
    echo "Useful Commands:"
    echo "  View logs:      heroku logs --tail --app $APP_NAME"
    echo "  Open app:       heroku open --app $APP_NAME"
    echo "  App info:       heroku apps:info --app $APP_NAME"
    echo "  Scale dynos:    heroku ps:scale web=1 --app $APP_NAME"
    echo ""
    
    heroku open --app $APP_NAME
else
    echo ""
    echo "========================================"
    echo "✗ DEPLOYMENT FAILED"
    echo "========================================"
    echo ""
    echo "Check the logs for errors:"
    echo "heroku logs --tail --app $APP_NAME"
    echo ""
    exit 1
fi
