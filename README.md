# Distributed Notification System

A scalable microservices system for sending email and push notifications asynchronously.

## Features

-  **5 Microservices** - API Gateway, User, Template, Email, Push
-  **Message Queue** - RabbitMQ for async processing
-  **Database per Service** - PostgreSQL isolation
-  **Redis Caching** - Fast user preferences & templates
-  **Fault Tolerance** - Circuit breaker & retry logic
-  **Email** - Gmail SMTP integration
-  **Push** - OneSignal integration

## Quick Start

### Local Development

#### Prerequisites
- Docker & Docker Compose
- Git

#### Setup

```bash
# Clone repository
git clone https://github.com/Kalanza/distributed-notification-system.git
cd distributed-notification-system

# Configure credentials
cp .env.example .env
# Edit .env with your SMTP and OneSignal credentials

# Start services
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

### Heroku Deployment

Deploy to Heroku with one command:

```bash
# Using the automated script (PowerShell)
.\deploy-heroku.ps1 -AppName "your-app-name" `
  -SmtpUser "your-email@gmail.com" `
  -SmtpPassword "your-app-password" `
  -SmtpFromEmail "noreply@yourdomain.com"

# Or using bash script
./deploy-heroku.sh your-app-name your-email@gmail.com app-password noreply@yourdomain.com
```

For detailed deployment instructions, see [HEROKU_DEPLOYMENT.md](HEROKU_DEPLOYMENT.md)

**Quick Heroku Setup:**
1. Install [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
2. Login: `heroku login`
3. Run deployment script above
4. Access your app at: `https://your-app-name.herokuapp.com/docs`

## Usage

### Send Notification

```bash
POST http://localhost:8000/notifications/send
Content-Type: application/json

{
  "user_id": 1,
  "channel": "email",
  "template_id": "welcome",
  "variables": {
    "name": "John"
  }
}
```

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **RabbitMQ Dashboard**: http://localhost:15672 (guest/guest)

## Architecture

```
Client  API Gateway  RabbitMQ  [Email Service, Push Service]
                          
                    [User Service, Template Service]
                          
                    PostgreSQL, Redis
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| API Gateway | 8000 | Entry point, rate limiting |
| User Service | 8003 | User management |
| Template Service | 8004 | Template management |
| Email Service | 8001 | Email processing |
| Push Service | 8002 | Push notifications |

## Configuration

Key environment variables in `.env`:

```bash
# Email
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Push Notifications
ONESIGNAL_APP_ID=your-app-id
ONESIGNAL_REST_API_KEY=your-api-key

# Rate Limiting
RATE_LIMIT_PER_USER=100
```

## Tech Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Message Queue**: RabbitMQ
- **Database**: PostgreSQL
- **Cache**: Redis
- **Deployment**: Docker Compose

## Monitoring

```bash
# View logs
docker-compose logs -f

# Check service status
docker-compose ps

# Stop services
docker-compose down
```

## Project Structure

```
 api_gateway/          # Entry point
 user_service/         # User management
 template_service/     # Templates
 email_service/        # Email sender
 push_service/         # Push sender
 shared/               # Utilities
    config/          # Settings
    schemas/         # Data models
    utils/           # Helpers
 docker-compose.yml    # Orchestration
```

## License

MIT License

## Author

[Kalanza](https://github.com/Kalanza)
