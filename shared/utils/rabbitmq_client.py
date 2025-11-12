import pika
from typing import Callable, Optional
import json
from shared.config.settings import settings
from shared.utils.logger import get_logger


logger = get_logger("rabbitmq_client")


class RabbitMQClient:
    """RabbitMQ client for message queue operations"""
    
    def __init__(self):
        self.host = settings.RABBITMQ_HOST
        self.port = settings.RABBITMQ_PORT
        self.exchange = settings.RABBITMQ_EXCHANGE
        self.connection = None
        self.channel = None
    
    def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(
                settings.RABBITMQ_USER,
                settings.RABBITMQ_PASS
            )
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            logger.info(f"Connected to RabbitMQ at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise
    
    def setup_exchange_and_queues(self):
        """Setup exchange, queues, and bindings"""
        if not self.channel:
            self.connect()
        
        # Declare exchange
        self.channel.exchange_declare(
            exchange=self.exchange,
            exchange_type='direct',
            durable=True
        )
        
        # Declare queues
        queues = ['email.queue', 'push.queue', 'failed.queue']
        for queue in queues:
            self.channel.queue_declare(queue=queue, durable=True)
        
        # Bind queues to exchange
        self.channel.queue_bind(
            exchange=self.exchange,
            queue='email.queue',
            routing_key='email'
        )
        self.channel.queue_bind(
            exchange=self.exchange,
            queue='push.queue',
            routing_key='push'
        )
        self.channel.queue_bind(
            exchange=self.exchange,
            queue='failed.queue',
            routing_key='failed'
        )
        
        logger.info("RabbitMQ exchange and queues setup complete")
    
    def publish_message(self, routing_key: str, message: dict, message_id: Optional[str] = None):
        """Publish message to exchange"""
        if not self.channel:
            self.connect()
        
        try:
            properties = pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type='application/json',
                message_id=message_id
            )
            
            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=routing_key,
                body=json.dumps(message),
                properties=properties
            )
            logger.info(f"Published message to {routing_key} queue", correlation_id=message.get('correlation_id'))
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
            raise
    
    def consume_messages(self, queue: str, callback: Callable, auto_ack: bool = False):
        """Consume messages from queue"""
        if not self.channel:
            self.connect()
        
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue=queue,
            on_message_callback=callback,
            auto_ack=auto_ack
        )
        
        logger.info(f"Started consuming from {queue}")
        self.channel.start_consuming()
    
    def send_to_dead_letter_queue(self, message: dict, reason: str):
        """Send failed message to dead letter queue"""
        message['failure_reason'] = reason
        self.publish_message('failed', message)
    
    def close(self):
        """Close connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("RabbitMQ connection closed")
    
    def health_check(self) -> bool:
        """Check if RabbitMQ is healthy"""
        try:
            if not self.connection or self.connection.is_closed:
                self.connect()
            return self.connection.is_open
        except Exception:
            return False


def get_rabbitmq_client() -> RabbitMQClient:
    """Get RabbitMQ client instance"""
    return RabbitMQClient()
