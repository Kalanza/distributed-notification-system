#!/usr/bin/env python
"""
Push Worker - Processes push notifications from RabbitMQ queue
Runs as a standalone worker without HTTP server
"""

import sys
import os
import json
from datetime import datetime
import signal

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.config.settings import settings
from shared.utils.logger import get_logger
from shared.utils.rabbitmq_client import get_rabbitmq_client
from shared.utils.redis_client import get_redis_client
from shared.utils.onesignal_client import get_onesignal_client
from shared.utils.circuit_breaker import circuit_breaker
from shared.utils.retry import retry_with_backoff
import asyncio

# Initialize logger
logger = get_logger("push_worker", settings.LOG_LEVEL)

# Initialize clients
rabbitmq_client = get_rabbitmq_client()
redis_client = get_redis_client()
onesignal_client = get_onesignal_client()

# Graceful shutdown flag
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Shutdown signal received, finishing current work...")


@circuit_breaker(failure_threshold=5, recovery_timeout=60, name="send_push_notification")
@retry_with_backoff(max_attempts=3, backoff_base=2)
def send_push_notification(player_ids: list, title: str, message: str, data: dict = None):
    """Send push notification via OneSignal"""
    try:
        # Check if OneSignal is configured
        if not settings.ONESIGNAL_APP_ID or not settings.ONESIGNAL_REST_API_KEY:
            logger.warning("OneSignal not configured. Using mock mode.")
            logger.info(f"[MOCK] Sending push to {len(player_ids)} device(s)...")
            logger.info(f"[MOCK] Title: {title}")
            logger.info(f"[MOCK] Message: {message}")
            logger.info(f"[MOCK] Data: {data}")
            return {"success": True, "mock": True}
        
        # Send via OneSignal
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                onesignal_client.send_notification(
                    player_ids=player_ids,
                    title=title,
                    message=message,
                    data=data or {},
                    url=data.get("action_url") if data else None,
                    priority=10
                )
            )
            logger.info(f"Push notification sent via OneSignal. Recipients: {result.get('recipients', 0)}")
            return result
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Push notification error: {str(e)}")
        raise


def generate_push_content(template_code: str, variables: dict):
    """Generate push notification content from template"""
    # Simple templates for now
    templates = {
        "welcome": {
            "title": "Welcome!",
            "message": f"Welcome {variables.get('name', 'User')}! Thanks for joining.",
            "data": {"action": "open_app", "screen": "home"}
        },
        "notification": {
            "title": "New Notification",
            "message": variables.get('message', 'You have a new notification'),
            "data": {"action": "open_notification", "id": variables.get('id', '')}
        }
    }
    
    return templates.get(template_code, templates["notification"])


def process_push_notification(data: dict):
    """Process a single push notification"""
    try:
        notification_id = data.get('notification_id')
        user_id = data.get('user_id')
        template_code = data.get('template_code')
        variables = data.get('variables', {})
        
        logger.info(f"Processing push notification {notification_id} for user {user_id}")
        
        # Get user device tokens (from Redis cache or user service)
        user_data = redis_client.get(f"user:{user_id}")
        
        if not user_data:
            logger.warning(f"User {user_id} not found in cache")
            # Use provided player_ids from variables if available
            player_ids = variables.get('player_ids', [])
            if not player_ids:
                player_ids = [variables.get('player_id', 'mock_player_id')]
        else:
            # Get OneSignal player IDs from user data
            player_ids = user_data.get('player_ids', [])
            if not player_ids:
                player_ids = ['mock_player_id']
        
        # Generate push content
        push_content = generate_push_content(template_code, variables)
        
        # Send to all user devices
        result = send_push_notification(
            player_ids=player_ids,
            title=push_content['title'],
            message=push_content['message'],
            data=push_content.get('data')
        )
        
        # Update status in Redis
        status_data = {
            "notification_id": notification_id,
            "status": "delivered",
            "timestamp": datetime.utcnow().isoformat(),
            "error": None,
            "onesignal_id": result.get('id') if not result.get('mock') else None,
            "recipients": result.get('recipients', len(player_ids))
        }
        redis_client.set(f"notification:status:{notification_id}", status_data, expire=86400)
        
        logger.info(f"Push notification {notification_id} delivered to {len(player_ids)} device(s)")
        
    except Exception as e:
        logger.error(f"Error processing push notification: {str(e)}")
        # Update status to failed
        status_data = {
            "notification_id": data.get('notification_id'),
            "status": "failed",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
        redis_client.set(
            f"notification:status:{data.get('notification_id')}",
            status_data,
            expire=86400
        )
        raise


def callback(ch, method, properties, body):
    """RabbitMQ message callback"""
    try:
        data = json.loads(body)
        logger.info(f"Received message: {data.get('notification_id')}")
        
        process_push_notification(data)
        
        # Acknowledge message
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        logger.error(f"Error in callback: {str(e)}")
        # Negative acknowledge - don't requeue
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    """Main worker loop"""
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("=" * 50)
    logger.info("Push Worker Starting...")
    logger.info(f"RabbitMQ Host: {settings.RABBITMQ_HOST}")
    logger.info(f"Redis Host: {settings.REDIS_HOST}")
    logger.info("=" * 50)
    
    try:
        # Connect to RabbitMQ
        rabbitmq_client.connect()
        logger.info("Connected to RabbitMQ")
        
        # Setup exchange and queues
        rabbitmq_client.setup_exchange_and_queues()
        logger.info("Exchange and queues configured")
        
        # Start consuming messages
        logger.info("Starting to consume from push.queue...")
        logger.info("Worker is ready. Waiting for messages...")
        logger.info("Press CTRL+C to exit")
        
        rabbitmq_client.consume_messages(
            queue='push.queue',
            callback=callback,
            auto_ack=False
        )
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise
    finally:
        logger.info("Shutting down push worker...")
        rabbitmq_client.close()
        logger.info("Push worker stopped")


if __name__ == "__main__":
    main()
