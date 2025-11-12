from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import requests
from shared.schemas.notification_schema import NotificationPayload
from shared.config.settings import settings
from shared.utils.logger import get_logger
from shared.utils.rabbitmq_client import get_rabbitmq_client
from shared.utils.redis_client import get_redis_client
from shared.utils.circuit_breaker import circuit_breaker, CircuitBreakerOpenException
from shared.utils.retry import retry_with_backoff, MaxRetriesExceededException
from shared.schemas.response_schema import create_success_response

# Initialize FastAPI app
app = FastAPI(
    title="Email Service - Notification System",
    description="Processes email notifications from queue",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize logger
logger = get_logger("email_service", settings.LOG_LEVEL)

# Initialize clients
rabbitmq_client = get_rabbitmq_client()
redis_client = get_redis_client()

# Service URLs
TEMPLATE_SERVICE_URL = "http://template_service:8000"
USER_SERVICE_URL = "http://user_service:8000"


@circuit_breaker(failure_threshold=5, recovery_timeout=60, name="send_smtp_email")
@retry_with_backoff(max_attempts=3, backoff_base=2)
def send_email_smtp(to_email: str, subject: str, body_text: str, body_html: str = None):
    """Send email via SMTP with circuit breaker and retry"""
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = settings.SMTP_FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Attach plain text
        part1 = MIMEText(body_text, 'plain')
        msg.attach(part1)
        
        # Attach HTML if provided
        if body_html:
            part2 = MIMEText(body_html, 'html')
            msg.attach(part2)
        
        # Send email
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {str(e)}")
        raise


def get_user_info(user_id: int):
    """Fetch user information from User Service"""
    try:
        response = requests.get(
            f"{USER_SERVICE_URL}/users/{user_id}",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('data')
        return None
    except Exception as e:
        logger.error(f"Error fetching user info: {str(e)}")
        return None


def get_user_preferences(user_id: int):
    """Fetch user preferences from User Service"""
    try:
        # Check cache first
        cached_prefs = redis_client.get_cached_user_preferences(user_id)
        if cached_prefs:
            return cached_prefs
        
        response = requests.get(
            f"{USER_SERVICE_URL}/users/{user_id}/preferences",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            prefs = data.get('data')
            # Cache preferences
            redis_client.cache_user_preferences(user_id, prefs)
            return prefs
        return None
    except Exception as e:
        logger.error(f"Error fetching user preferences: {str(e)}")
        return None


def render_template(template_id: str, variables: dict, language: str = "en"):
    """Render template from Template Service"""
    try:
        response = requests.post(
            f"{TEMPLATE_SERVICE_URL}/templates/render",
            json={
                "template_id": template_id,
                "variables": variables,
                "language": language
            },
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('data')
        return None
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        return None


def process_email_notification(payload: NotificationPayload):
    """Process email notification"""
    correlation_id = payload.correlation_id
    
    try:
        logger.log_notification_lifecycle(
            stage="processing",
            request_id=payload.request_id,
            correlation_id=correlation_id,
            status="processing",
            channel="email"
        )
        
        # Get user info
        user_info = get_user_info(payload.user_id)
        if not user_info:
            raise Exception("User not found")
        
        # Get user preferences
        preferences = get_user_preferences(payload.user_id)
        if preferences and not preferences.get('email_enabled'):
            logger.warning(
                f"Email notifications disabled for user {payload.user_id}",
                correlation_id=correlation_id
            )
            return
        
        # Add user info to variables
        full_variables = {
            **payload.variables,
            'user_email': user_info.get('email'),
            'username': user_info.get('username')
        }
        
        # Render template
        rendered = render_template(
            payload.template_id,
            full_variables,
            preferences.get('language', 'en') if preferences else 'en'
        )
        
        if not rendered:
            raise Exception("Failed to render template")
        
        # Send email
        send_email_smtp(
            to_email=user_info.get('email'),
            subject=rendered.get('subject', 'Notification'),
            body_text=rendered.get('body_text'),
            body_html=rendered.get('body_html')
        )
        
        # Update status
        status_key = f"notification:status:{payload.request_id}"
        status_data = redis_client.get(status_key)
        if status_data:
            status_data['status'] = 'sent'
            status_data['delivered_at'] = datetime.utcnow().isoformat()
            status_data['updated_at'] = datetime.utcnow().isoformat()
            redis_client.set(status_key, status_data, expire=86400)
        
        logger.log_notification_lifecycle(
            stage="sent",
            request_id=payload.request_id,
            correlation_id=correlation_id,
            status="sent",
            channel="email",
            recipient=user_info.get('email')
        )
        
    except CircuitBreakerOpenException as e:
        logger.error(
            f"Circuit breaker open for email: {str(e)}",
            correlation_id=correlation_id
        )
        # Requeue message
        rabbitmq_client.publish_message('email', payload.model_dump())
        
    except MaxRetriesExceededException as e:
        logger.error(
            f"Max retries exceeded for email: {str(e)}",
            correlation_id=correlation_id
        )
        # Send to dead letter queue
        rabbitmq_client.send_to_dead_letter_queue(
            payload.model_dump(),
            reason="Max retries exceeded"
        )
        
        # Update status
        status_key = f"notification:status:{payload.request_id}"
        status_data = redis_client.get(status_key)
        if status_data:
            status_data['status'] = 'failed'
            status_data['error_message'] = str(e)
            status_data['updated_at'] = datetime.utcnow().isoformat()
            redis_client.set(status_key, status_data, expire=86400)
        
    except Exception as e:
        logger.error(
            f"Error processing email notification: {str(e)}",
            correlation_id=correlation_id
        )
        # Requeue for retry
        rabbitmq_client.publish_message('email', payload.model_dump())


def consume_email_queue():
    """Consume messages from email queue"""
    def callback(ch, method, properties, body):
        try:
            data = json.loads(body)
            payload = NotificationPayload(**data)
            
            logger.info(
                f"Received email notification for user {payload.user_id}",
                correlation_id=payload.correlation_id
            )
            
            process_email_notification(payload)
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Error in email callback: {str(e)}")
            # Reject and requeue
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    try:
        rabbitmq_client.connect()
        rabbitmq_client.consume_messages(
            queue='email.queue',
            callback=callback,
            auto_ack=False
        )
    except Exception as e:
        logger.error(f"Error consuming email queue: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Start consuming email queue on startup"""
    logger.info("Starting Email Service...")
    Thread(target=consume_email_queue, daemon=True).start()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "service": "email_service",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": {
            "rabbitmq": rabbitmq_client.health_check(),
            "redis": redis_client.health_check()
        }
    }
    
    all_healthy = all(health_status["dependencies"].values())
    if not all_healthy:
        health_status["status"] = "degraded"
    
    return create_success_response(
        data=health_status,
        message="Health check completed"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
