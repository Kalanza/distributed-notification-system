"""
Test configuration and fixtures
"""
import pytest
from unittest.mock import Mock, MagicMock


@pytest.fixture
def mock_rabbitmq_client():
    """Mock RabbitMQ client for testing"""
    client = Mock()
    client.connect = Mock()
    client.publish_message = Mock()
    client.consume_messages = Mock()
    client.health_check = Mock(return_value=True)
    client.close = Mock()
    return client


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing"""
    client = Mock()
    client.get = Mock(return_value=None)
    client.set = Mock(return_value=True)
    client.delete = Mock(return_value=True)
    client.health_check = Mock(return_value=True)
    client.check_rate_limit = Mock(return_value=(True, 10))
    return client


@pytest.fixture
def sample_notification_payload():
    """Sample notification payload for testing"""
    return {
        "request_id": "test-request-123",
        "user_id": 1,
        "channel": "email",
        "template_id": "welcome",
        "variables": {"name": "Test User", "action_url": "https://example.com"},
        "priority": "high",
        "correlation_id": "test-correlation-123"
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "user_id": 1,
        "email": "test@example.com",
        "device_token": "test-device-token-123",
        "preferences": {
            "email_enabled": True,
            "push_enabled": True
        }
    }


@pytest.fixture
def sample_template():
    """Sample template for testing"""
    return {
        "template_id": "welcome",
        "subject": "Welcome {{name}}!",
        "body_html": "<h1>Welcome {{name}}</h1><p>Click <a href='{{action_url}}'>here</a></p>",
        "body_text": "Welcome {{name}}! Click here: {{action_url}}"
    }
