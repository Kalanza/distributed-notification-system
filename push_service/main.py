from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread
import json
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
    title="Push Service - Notification System",
    description="Processes push notifications from queue",
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
logger = get_logger("push_service", settings.LOG_LEVEL)

# Initialize clients
rabbitmq_client = get_rabbitmq_client()
redis_client = get_redis_client()

# Service URLs
TEMPLATE_SERVICE_URL = "http://template_service:8000"
USER_SERVICE_URL = "http://user_service:8000"

# OneSignal endpoint
ONESIGNAL_API_URL = settings.ONESIGNAL_API_URL


@circuit_breaker(failure_threshold=5, recovery_timeout=60, name="send_onesignal_push")
@retry_with_backoff(max_attempts=3, backoff_base=2)
def send_push_onesignal(user_id: int, title: str, body: str, data: dict = None, image_url: str = None):
    """Send push notification via OneSignal with circuit breaker and retry"""
    try:
        if not settings.ONESIGNAL_APP_ID or not settings.ONESIGNAL_REST_API_KEY:
            logger.warning("OneSignal not configured. Simulating push notification.")
            logger.info(f"[SIMULATED] Push to user {user_id}: {title} - {body}")
            return True
        
        # Prepare OneSignal payload
        payload = {
            "app_id": settings.ONESIGNAL_APP_ID,
            "include_external_user_ids": [str(user_id)],  # Use your user ID as external ID
            "headings": {"en": title},
            "contents": {"en": body},
            "data": data or {}
        }
        
        # Add image if provided
        if image_url:
            payload["big_picture"] = image_url
            payload["large_icon"] = image_url
        
        # Send to OneSignal
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Basic {settings.ONESIGNAL_REST_API_KEY}"
        }
        
        response = requests.post(
            ONESIGNAL_API_URL,
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            recipients = result.get('recipients', 0)
            if recipients > 0:
                logger.info(f"Push notification sent successfully to user {user_id} (recipients: {recipients})")
                return True
            else:
                logger.warning(f"Push notification sent but no recipients found for user {user_id}")
                # Not throwing error as user might not have app installed yet
                return True
        else:
            error_msg = response.json() if response.text else f"Status {response.status_code}"
            raise Exception(f"OneSignal error: {error_msg}")
            
    except Exception as e:
        logger.error(f"Error sending push notification: {str(e)}")
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


def process_push_notification(payload: NotificationPayload):
    """Process push notification"""
    correlation_id = payload.correlation_id
    
    try:
        logger.log_notification_lifecycle(
            stage="processing",
            request_id=payload.request_id,
            correlation_id=correlation_id,
            status="processing",
            channel="push"
        )
        
        # Get user info
        user_info = get_user_info(payload.user_id)
        if not user_info:
            raise Exception("User not found")
        
        # Get user preferences
        preferences = get_user_preferences(payload.user_id)
        if not preferences:
            raise Exception("User preferences not found")
        
        # Check if push notifications are enabled
        if not preferences.get('push_enabled'):
            logger.warning(
                f"Push notifications disabled for user {payload.user_id}",
                correlation_id=correlation_id
            )
            return
        
        # Note: OneSignal uses external_user_ids (your user_id) instead of device tokens
        # Users need to call OneSignal SDK to register with your user_id
        
        # Add user info to variables
        full_variables = {
            **payload.variables,
            'username': user_info.get('username')
        }
        
        # Render template
        rendered = render_template(
            payload.template_id,
            full_variables,
            preferences.get('language', 'en')
        )
        
        if not rendered:
            raise Exception("Failed to render template")
        
        # Extract title and body for push notification
        title = rendered.get('subject', 'Notification')
        body = rendered.get('body_text', '')
        
        # Send push notification via OneSignal
        send_push_onesignal(
            user_id=payload.user_id,
            title=title,
            body=body,
            data=payload.variables,
            image_url=payload.variables.get('image_url')
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
            channel="push",
            user_id=payload.user_id
        )
        
    except CircuitBreakerOpenException as e:
        logger.error(
            f"Circuit breaker open for push: {str(e)}",
            correlation_id=correlation_id
        )
        # Requeue message
        rabbitmq_client.publish_message('push', payload.model_dump())
        
    except MaxRetriesExceededException as e:
        logger.error(
            f"Max retries exceeded for push: {str(e)}",
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
            f"Error processing push notification: {str(e)}",
            correlation_id=correlation_id
        )
        # Requeue for retry
        rabbitmq_client.publish_message('push', payload.model_dump())


def consume_push_queue():
    """Consume messages from push queue"""
    def callback(ch, method, properties, body):
        try:
            data = json.loads(body)
            payload = NotificationPayload(**data)
            
            logger.info(
                f"Received push notification for user {payload.user_id}",
                correlation_id=payload.correlation_id
            )
            
            process_push_notification(payload)
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        except Exception as e:
            logger.error(f"Error in push callback: {str(e)}")
            # Reject and requeue
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    try:
        rabbitmq_client.connect()
        rabbitmq_client.consume_messages(
            queue='push.queue',
            callback=callback,
            auto_ack=False
        )
    except Exception as e:
        logger.error(f"Error consuming push queue: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Start consuming push queue on startup"""
    logger.info("Starting Push Service...")
    Thread(target=consume_push_queue, daemon=True).start()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        "service": "push_service",
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
