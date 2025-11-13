#!/usr/bin/env python
"""
Email Worker - Processes email notifications from RabbitMQ queue
Runs as a standalone worker without HTTP server
"""

import sys
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import signal

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.config.settings import settings
from shared.utils.logger import get_logger
from shared.utils.rabbitmq_client import get_rabbitmq_client
from shared.utils.redis_client import get_redis_client
from shared.utils.circuit_breaker import circuit_breaker
from shared.utils.retry import retry_with_backoff

# Initialize logger
logger = get_logger("email_worker", settings.LOG_LEVEL)

# Initialize clients
rabbitmq_client = get_rabbitmq_client()
redis_client = get_redis_client()

# Graceful shutdown flag
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Shutdown signal received, finishing current work...")


@circuit_breaker(failure_threshold=5, recovery_timeout=60, name="send_smtp_email")
@retry_with_backoff(max_attempts=3, backoff_base=2)
def send_email_smtp(to_email: str, subject: str, body_text: str, body_html: str = None):
    """Send email via SMTP with circuit breaker and retry"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = settings.SMTP_FROM_EMAIL
        msg['To'] = to_email

        # Attach text and HTML parts
        part1 = MIMEText(body_text, 'plain')
        msg.attach(part1)
        
        if body_html:
            part2 = MIMEText(body_html, 'html')
            msg.attach(part2)

        # Send email
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            
        logger.info(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"SMTP error: {str(e)}")
        raise


def generate_email_content(template_code: str, variables: dict):
    """Generate email content from template"""
    # For now, use simple templates
    # In production, fetch from template service
    
    templates = {
        "welcome": {
            "subject": "Welcome to Our Service!",
            "body_text": f"Hello {variables.get('name', 'User')}!\n\nWelcome to our service. Click here to get started: {variables.get('link', '#')}",
            "body_html": f"""
                <html>
                <body>
                    <h1>Welcome {variables.get('name', 'User')}!</h1>
                    <p>Thank you for joining our service.</p>
                    <p><a href="{variables.get('link', '#')}">Get Started</a></p>
                    <p>Best regards,<br>The Team</p>
                </body>
                </html>
            """
        },
        "notification": {
            "subject": "New Notification",
            "body_text": f"Hello {variables.get('name', 'User')}!\n\nYou have a new notification: {variables.get('message', 'Check your account')}",
            "body_html": f"""
                <html>
                <body>
                    <h2>New Notification</h2>
                    <p>Hello {variables.get('name', 'User')}!</p>
                    <p>{variables.get('message', 'You have a new notification.')}</p>
                    <p><a href="{variables.get('link', '#')}">View Details</a></p>
                </body>
                </html>
            """
        }
    }
    
    template = templates.get(template_code, templates["notification"])
    return template


def process_email_notification(data: dict):
    """Process a single email notification"""
    try:
        notification_id = data.get('notification_id')
        user_id = data.get('user_id')
        template_code = data.get('template_code')
        variables = data.get('variables', {})
        
        logger.info(f"Processing email notification {notification_id} for user {user_id}")
        
        # Get user email (from Redis cache or would be from user service in production)
        user_data = redis_client.get(f"user:{user_id}")
        
        if not user_data:
            logger.warning(f"User {user_id} not found, using variables email")
            to_email = variables.get('email', settings.SMTP_FROM_EMAIL)
        else:
            to_email = user_data.get('email')
        
        # Generate email content
        email_content = generate_email_content(template_code, variables)
        
        # Send email
        send_email_smtp(
            to_email=to_email,
            subject=email_content['subject'],
            body_text=email_content['body_text'],
            body_html=email_content.get('body_html')
        )
        
        # Update status in Redis
        status_data = {
            "notification_id": notification_id,
            "status": "delivered",
            "timestamp": datetime.utcnow().isoformat(),
            "error": None
        }
        redis_client.set(f"notification:status:{notification_id}", status_data, expire=86400)
        
        logger.info(f"Email notification {notification_id} delivered successfully")
        
    except Exception as e:
        logger.error(f"Error processing email notification: {str(e)}")
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
        
        process_email_notification(data)
        
        # Acknowledge message
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        logger.error(f"Error in callback: {str(e)}")
        # Negative acknowledge - requeue the message
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    """Main worker loop"""
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("=" * 50)
    logger.info("Email Worker Starting...")
    logger.info(f"RabbitMQ Host: {settings.RABBITMQ_HOST}")
    logger.info(f"Redis Host: {settings.REDIS_HOST}")
    logger.info(f"SMTP Host: {settings.SMTP_HOST}")
    logger.info("=" * 50)
    
    try:
        # Connect to RabbitMQ
        rabbitmq_client.connect()
        logger.info("Connected to RabbitMQ")
        
        # Setup exchange and queues
        rabbitmq_client.setup_exchange_and_queues()
        logger.info("Exchange and queues configured")
        
        # Start consuming messages
        logger.info("Starting to consume from email.queue...")
        logger.info("Worker is ready. Waiting for messages...")
        logger.info("Press CTRL+C to exit")
        
        rabbitmq_client.consume_messages(
            queue='email.queue',
            callback=callback,
            auto_ack=False
        )
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise
    finally:
        logger.info("Shutting down email worker...")
        rabbitmq_client.close()
        logger.info("Email worker stopped")


if __name__ == "__main__":
    main()
