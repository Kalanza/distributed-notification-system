# Heroku Worker Services Setup

## Current Status

✅ **API Gateway** - Running on web dyno
✅ **RabbitMQ** - CloudAMQP (Free tier)
✅ **Redis** - Heroku Redis (Mini plan)
✅ **PostgreSQL** - Heroku Postgres (Essential-0 plan)

⚠️ **Worker Services** - Not yet deployed

## Understanding the Architecture

Your notification system has **5 microservices**:

1. **API Gateway** (web dyno) - Entry point, queues notifications
2. **Email Service** (worker) - Consumes email queue, sends emails
3. **Push Service** (worker) - Consumes push queue, sends push notifications
4. **User Service** (worker) - Manages user data
5. **Template Service** (worker) - Manages notification templates

## Current Behavior

- ✅ Notifications are **queued successfully** in RabbitMQ
- ⏸️ Notifications **stay in queue** until workers are deployed
- 📬 **No emails sent yet** because email worker isn't running

## Option 1: Deploy Email Worker (Recommended for Testing)

Deploy just the email service to start sending emails:

### Create Procfile for Email Worker

```bash
worker: cd email_service && python main.py
```

### Update heroku.yml

The current Heroku setup only runs the API Gateway. To add workers, you need to:

1. **Manual Scaling** (Easiest for testing):
   ```powershell
   # Note: Each worker dyno costs money on Heroku
   # Free tier only supports 1 dyno at a time
   
   # This won't work on free tier, but here's how you'd do it:
   heroku ps:scale worker=1 --app distributed-notif-system-3037
   ```

2. **Combined Worker** (Better for free tier):
   Create a single worker that handles all background tasks

## Option 2: Combined Worker for Free Tier

Since Heroku's free/hobby tier limits you to 1 web dyno, the most cost-effective approach is to either:

### A) Run workers locally and connect to Heroku services:
```powershell
# Get your add-on credentials
heroku config --app distributed-notif-system-3037

# Set them as local environment variables
$env:CLOUDAMQP_URL="amqps://user:pass@host/vhost"
$env:REDIS_URL="redis://h:pass@host:port"
$env:DATABASE_URL="postgres://user:pass@host:port/db"
$env:SMTP_USER="kalanzavictor@gmail.com"
$env:SMTP_PASSWORD="vywh dwkh hakd reka"
$env:SMTP_FROM_EMAIL="kalanzavictor@gmail.com"

# Run email service locally
cd email_service
python main.py
```

### B) Use Heroku Scheduler (Free Add-on):
```powershell
# Add scheduler
heroku addons:create scheduler:standard --app distributed-notif-system-3037

# Open scheduler dashboard
heroku addons:open scheduler --app distributed-notif-system-3037

# Add a job to process queue every 10 minutes:
# Command: cd email_service && python -c "from main import process_notifications; process_notifications()"
```

### C) Upgrade to Paid Dyno Plan:
```powershell
# Upgrade to Basic plan ($7/month per dyno)
heroku ps:type web=basic --app distributed-notif-system-3037

# Add worker dyno for email service
# You'll need to create a separate Procfile entry
heroku ps:scale worker=1 --app distributed-notif-system-3037
```

## Option 3: Use Heroku with Multiple Apps (Free)

Deploy each service as a separate Heroku app (all using same add-ons):

```powershell
# Create separate apps
heroku create distributed-notif-email-worker
heroku create distributed-notif-push-worker

# Link them to same add-ons
heroku addons:attach distributed-notif-system-3037::CLOUDAMQP --app distributed-notif-email-worker
heroku addons:attach distributed-notif-system-3037::REDIS --app distributed-notif-email-worker
heroku addons:attach distributed-notif-system-3037::DATABASE --app distributed-notif-email-worker

# Deploy email worker
git subtree push --prefix email_service heroku-email main
```

## Recommended Approach for You

### 🎯 Best Option: Run Workers Locally

Since you're testing and on the free tier:

1. Keep API Gateway on Heroku (already deployed ✅)
2. Run email worker locally (connects to Heroku RabbitMQ)
3. This costs **$0 extra** and works perfectly for development

### Steps to Run Email Worker Locally:

```powershell
# 1. Get Heroku config
heroku config --app distributed-notif-system-3037 | Out-File heroku-config.txt

# 2. Set environment variables (from the config output)
$env:CLOUDAMQP_URL="<your-cloudamqp-url>"
$env:REDIS_URL="<your-redis-url>"
$env:DATABASE_URL="<your-database-url>"
$env:SMTP_USER="kalanzavictor@gmail.com"
$env:SMTP_PASSWORD="vywh dwkh hakd reka"
$env:SMTP_FROM_EMAIL="kalanzavictor@gmail.com"
$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:PYTHONPATH="C:\Users\USER\Desktop\distributed-notification-system"

# 3. Install dependencies
pip install -r email_service/requirements.txt

# 4. Run email worker
cd email_service
python main.py
```

## Testing Email Delivery

Once your worker is running (locally or on Heroku):

```powershell
# Send a test notification (will be processed by worker)
$notif = '{"user_id":"bf9a226a-db88-431d-8cdc-2dd67db08e23","notification_type":"email","template_code":"welcome","variables":{"name":"Test User","link":"https://example.com"},"priority":5}'
Invoke-RestMethod -Uri "https://distributed-notif-system-3037-a8c646106fe0.herokuapp.com/api/v1/notifications/" -Method Post -Body $notif -ContentType "application/json"

# Check your email inbox: kalanzavictor@gmail.com
```

## Cost Comparison

| Setup | Cost/Month | Pros | Cons |
|-------|------------|------|------|
| **API only (current)** | $8 | Cheap, good for learning | No email sending |
| **API + Local workers** | $8 | Cheap, full functionality | Must run locally |
| **API + 1 Worker dyno** | $15 | Fully cloud-based | Costs more |
| **All services on Heroku** | $35+ | Production-ready | Expensive |

## Next Steps

Choose your preferred approach:

1. **Test Now (Recommended)**: Run email worker locally
2. **Later**: Upgrade to paid dyno to run workers on Heroku
3. **Production**: Consider AWS ECS, Google Cloud Run, or DigitalOcean

Let me know which approach you'd like to take, and I'll help you set it up!
