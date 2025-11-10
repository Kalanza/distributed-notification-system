# Distributed Notification System

A microservices-based notification system built with FastAPI, RabbitMQ, Redis, and PostgreSQL.

## Features

- Multi-channel notifications (Email, Push)
- Asynchronous message processing via RabbitMQ
- Microservices architecture with Docker
- Independent service scaling
- Health monitoring

## Architecture

## Architecture

**Services:**
- API Gateway (Port 8000) - Entry point for notification requests
- Email Service (Port 8001) - Email notification processing
- Push Service (Port 8002) - Push notification processing
- User Service (Port 8003) - User management
- Template Service (Port 8004) - Notification templates

**Infrastructure:**
- RabbitMQ (Ports 5672, 15672) - Message broker
- Redis (Port 6379) - Caching
- PostgreSQL - Database per service

## Quick Start

```bash
# Start all services
docker-compose up -d

# Check health
curl http://localhost:8000/health

# Send notification
curl -X POST http://localhost:8000/notifications/send \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "test-001",
    "user_id": 123,
    "channel": "email",
    "template_id": "welcome",
    "variables": {"name": "John"}
  }'

# Stop services
docker-compose down
```

## Development Status

- ✅ Day 1: Basic microservices setup with Docker
- ✅ Day 2: RabbitMQ integration for async messaging
- 🚧 Day 3+: Database integration, user preferences, external APIs

## Author

Kalanza - [GitHub](https://github.com/Kalanza)
