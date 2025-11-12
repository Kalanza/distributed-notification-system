# Distributed Notification System

A scalable, fault-tolerant microservices-based notification system that sends emails and push notifications asynchronously through message queues.

## 🏗️ System Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       v
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                             │
│  - Request Validation  - Rate Limiting  - Status Tracking   │
└────────┬────────────────────────────────────────────────────┘
         │
         v
┌─────────────────────────────────────────────────────────────┐
│                    RabbitMQ Exchange                         │
│         (notifications.direct)                               │
└───┬─────────────────────────────────────────────────┬───────┘
    │                                                   │
    v                                                   v
┌───────────────┐                             ┌───────────────┐
│ email.queue   │                             │  push.queue   │
└───────┬───────┘                             └───────┬───────┘
        │                                             │
        v                                             v
┌────────────────────┐                       ┌────────────────────┐
│  Email Service     │                       │  Push Service      │
│  - SMTP Sending    │                       │  - FCM Integration │
│  - Template Render │                       │  - Token Validate  │
│  - Retry Logic     │                       │  - Rich Notifs     │
└────────┬───────────┘                       └────────┬───────────┘
         │                                             │
         └─────────────────┬───────────────────────────┘
                           │
                           v
                  ┌────────────────┐
                  │ failed.queue   │
                  │ (Dead Letter)  │
                  └────────────────┘

Supporting Services:
┌─────────────┐  ┌──────────────────┐  ┌──────────┐
│User Service │  │Template Service  │  │  Redis   │
│- User Data  │  │- Templates       │  │- Caching │
│- Preferences│  │- Rendering       │  │- Rate    │
│- PostgreSQL │  │- Versioning      │  │  Limiting│
└─────────────┘  └──────────────────┘  └──────────┘
```

## ✨ Features

### Core Features
- ✅ **Microservices Architecture** - Independent, scalable services
- ✅ **Asynchronous Processing** - Message queue-based communication
- ✅ **Multi-Channel Support** - Email and Push notifications
- ✅ **Template Management** - Dynamic templates with variable substitution
- ✅ **User Management** - User preferences and contact info
- ✅ **Idempotency** - Prevent duplicate notifications
- ✅ **Rate Limiting** - Protect against abuse

### Resilience Features
- ✅ **Circuit Breaker Pattern** - Prevent cascading failures
- ✅ **Retry with Exponential Backoff** - Automatic retry logic
- ✅ **Dead Letter Queue** - Handle permanently failed messages
- ✅ **Health Checks** - Monitor service health
- ✅ **Correlation IDs** - Distributed tracing
- ✅ **Comprehensive Logging** - Track notification lifecycle

### Performance Features
- ✅ **Redis Caching** - Cache user preferences and templates
- ✅ **Horizontal Scaling** - Scale services independently
- ✅ **Connection Pooling** - Efficient database connections
- ✅ **Persistent Messages** - Durable message queues

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/Kalanza/distributed-notification-system.git
cd distributed-notification-system
```

2. **Configure environment variables**
```bash
# Create .env file with your configuration
# SMTP_USER=your-email@gmail.com
# SMTP_PASSWORD=your-app-password
# FCM_SERVER_KEY=your-fcm-server-key
```

3. **Start all services**
```bash
docker-compose up -d
```

4. **Verify services are running**
```bash
# Check all services
docker-compose ps

# Check API Gateway health
curl http://localhost:8000/health
```

## 📋 API Documentation

### API Gateway Endpoints

#### Send Notification
```http
POST /notifications/send
Content-Type: application/json

{
  "user_id": 1,
  "channel": "email",
  "template_id": "welcome_email",
  "variables": {
    "name": "John Doe",
    "action_url": "https://example.com/verify"
  },
  "priority": "high"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "request_id": "uuid-here",
    "status": "queued",
    "channel": "email",
    "correlation_id": "uuid-here",
    "remaining_requests": 99
  },
  "error": null,
  "message": "Notification queued successfully for email",
  "meta": null
}
```

### User Service Endpoints

#### Create User
```http
POST /users
Content-Type: application/json

{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword"
}
```

#### Update User Preferences
```http
PUT /users/{user_id}/preferences
Content-Type: application/json

{
  "email_enabled": true,
  "push_enabled": true,
  "push_token": "fcm-token-here",
  "language": "en"
}
```

### Template Service Endpoints

#### Create Template
```http
POST /templates
Content-Type: application/json

{
  "template_id": "welcome_email",
  "name": "Welcome Email",
  "channel": "email",
  "subject": "Welcome {{name}}!",
  "body_text": "Hello {{name}}, welcome!",
  "variables": ["name"]
}
```

## 🔧 Configuration

### Key Environment Variables

```bash
# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# FCM Configuration
FCM_SERVER_KEY=your-fcm-server-key

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60

# Retry Configuration
MAX_RETRY_ATTEMPTS=3

# Rate Limiting
RATE_LIMIT_PER_USER=100
RATE_LIMIT_WINDOW=60
```

## 🔄 Failure Handling

### Circuit Breaker
- Opens after 5 consecutive failures
- Stays open for 60 seconds
- Prevents cascading failures

### Retry Logic
- 1st retry: 2 seconds
- 2nd retry: 4 seconds
- 3rd retry: 8 seconds
- After 3 failures → Dead Letter Queue

## 📈 Performance Targets

- ✅ Handle 1,000+ notifications per minute
- ✅ API Gateway response under 100ms
- ✅ 99.5% delivery success rate
- ✅ Horizontal scaling support

## 🛠️ Tech Stack

- **Languages**: Python 3.11+
- **Frameworks**: FastAPI, Pydantic, SQLAlchemy
- **Message Queue**: RabbitMQ
- **Databases**: PostgreSQL
- **Caching**: Redis
- **Containerization**: Docker

## 📊 Monitoring

### Health Checks
- API Gateway: http://localhost:8000/health
- User Service: http://localhost:8003/health
- Template Service: http://localhost:8004/health
- Email Service: http://localhost:8001/health
- Push Service: http://localhost:8002/health

### RabbitMQ Management UI
http://localhost:15672 (guest/guest)

## 📝 Project Structure
```
distributed-notification-system/
├── api_gateway/          # API Gateway service
├── user_service/         # User management
├── template_service/     # Template management
├── email_service/        # Email processing
├── push_service/         # Push notifications
├── shared/               # Shared utilities
│   ├── config/          # Configuration
│   ├── schemas/         # Pydantic models
│   └── utils/           # Circuit breaker, retry, etc.
├── .github/workflows/    # CI/CD
└── docker-compose.yml    # Docker config
```

## 📄 License

MIT License - see [LICENSE](LICENSE)

## 👥 Team

Built as part of Stage 4 Backend Task

---

**Built with ❤️ by the Notification System Team**

## Development Status

- ✅ Day 1: Basic microservices setup with Docker
- ✅ Day 2: RabbitMQ integration for async messaging
- 🚧 Day 3+: Database integration, user preferences, external APIs

## Author

Kalanza - [GitHub](https://github.com/Kalanza)
