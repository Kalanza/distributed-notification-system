# Distributed Notification System

A scalable microservices-based notification system for sending email and push notifications asynchronously.

## Features

- **5 Microservices** - API Gateway, User, Template, Email, Push
- **Message Queue** - RabbitMQ for async processing
- **Database Isolation** - PostgreSQL per service
- **Redis Caching** - User preferences & rate limiting
- **Fault Tolerance** - Circuit breaker & retry logic
- **Email** - SMTP integration
- **Push** - OneSignal integration

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+

### Local Setup

```bash
# Clone repository
git clone https://github.com/Kalanza/distributed-notification-system.git
cd distributed-notification-system

# Start all services
docker-compose up -d

# Verify health
curl http://localhost:8000/health
```

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Architecture

```
Client → API Gateway → RabbitMQ → [Email/Push Services]
            ↓              ↓
       [User/Template]  PostgreSQL
            ↓
          Redis
```

## Tech Stack

- Python 3.11+ | FastAPI
- RabbitMQ | PostgreSQL | Redis
- Docker | Heroku

## Services

| Service | Port | Purpose |
|---------|------|---------|
| API Gateway | 8000 | Entry point, validation, rate limiting |
| User Service | 8003 | User management |
| Template Service | 8004 | Notification templates |
| Email Service | 8001 | Email processing |
| Push Service | 8002 | Push notifications |

## License

MIT License

## Author

[Kalanza](https://github.com/Kalanza)
