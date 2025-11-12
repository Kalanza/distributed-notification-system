"""
Tests for shared schemas
"""
import pytest
from pydantic import ValidationError
from shared.schemas.notification_schema import NotificationPayload, EmailNotification, PushNotification


class TestNotificationPayload:
    """Test NotificationPayload schema"""
    
    def test_valid_email_notification(self):
        """Test creating valid email notification payload"""
        payload = NotificationPayload(
            user_id=1,
            channel="email",
            template_id="welcome",
            variables={"name": "John"}
        )
        assert payload.user_id == 1
        assert payload.channel == "email"
        assert payload.template_id == "welcome"
        assert payload.priority == "medium"  # default
        assert payload.request_id is not None
        assert payload.correlation_id is not None
    
    def test_valid_push_notification(self):
        """Test creating valid push notification payload"""
        payload = NotificationPayload(
            user_id=2,
            channel="push",
            template_id="alert",
            variables={"message": "Test"},
            priority="high"
        )
        assert payload.user_id == 2
        assert payload.channel == "push"
        assert payload.priority == "high"
    
    def test_invalid_channel(self):
        """Test that invalid channel raises validation error"""
        with pytest.raises(ValidationError) as exc_info:
            NotificationPayload(
                user_id=1,
                channel="sms",  # invalid channel
                template_id="test"
            )
        assert "Channel must be 'email' or 'push'" in str(exc_info.value)
    
    def test_missing_required_fields(self):
        """Test that missing required fields raises validation error"""
        with pytest.raises(ValidationError):
            NotificationPayload(channel="email")  # missing user_id and template_id


class TestEmailNotification:
    """Test EmailNotification schema"""
    
    def test_valid_email_notification(self):
        """Test creating valid email notification"""
        email = EmailNotification(
            to_email="test@example.com",
            subject="Test Subject",
            body_html="<h1>Test</h1>"
        )
        assert email.to_email == "test@example.com"
        assert email.subject == "Test Subject"
        assert email.body_html == "<h1>Test</h1>"
        assert email.body_text is None  # optional
    
    def test_email_with_all_fields(self):
        """Test email notification with all fields"""
        email = EmailNotification(
            to_email="test@example.com",
            subject="Test",
            body_html="<p>HTML</p>",
            body_text="Plain text",
            from_email="sender@example.com",
            reply_to="reply@example.com"
        )
        assert email.from_email == "sender@example.com"
        assert email.reply_to == "reply@example.com"


class TestPushNotification:
    """Test PushNotification schema"""
    
    def test_valid_push_notification(self):
        """Test creating valid push notification"""
        push = PushNotification(
            device_token="token123",
            title="Test Title",
            body="Test Body"
        )
        assert push.device_token == "token123"
        assert push.title == "Test Title"
        assert push.body == "Test Body"
        assert push.sound == "default"  # default value
    
    def test_push_with_all_fields(self):
        """Test push notification with all fields"""
        push = PushNotification(
            device_token="token123",
            title="Alert",
            body="Important message",
            image_url="https://example.com/image.png",
            action_url="https://example.com/action",
            badge=5,
            sound="custom",
            data={"key": "value"}
        )
        assert push.image_url == "https://example.com/image.png"
        assert push.badge == 5
        assert push.data == {"key": "value"}
