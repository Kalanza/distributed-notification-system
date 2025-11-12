"""
Tests for shared schemas
"""
import pytest
from pydantic import ValidationError, HttpUrl
from shared.schemas.notification_schema import (
    NotificationPayload,
    NotificationType,
    NotificationStatus,
    UserData,
    UserCreate,
    UserPreference,
    EmailNotification,
    PushNotification
)


class TestNotificationPayload:
    """Test NotificationPayload schema"""
    
    def test_valid_email_notification(self):
        """Test creating valid email notification payload"""
        user_data = UserData(
            name="John Doe",
            link="https://example.com",
            meta={"key": "value"}
        )
        payload = NotificationPayload(
            notification_type=NotificationType.email,
            user_id="123e4567-e89b-12d3-a456-426614174000",
            template_code="welcome",
            variables=user_data,
            priority=5
        )
        assert payload.notification_type == NotificationType.email
        assert payload.user_id == "123e4567-e89b-12d3-a456-426614174000"
        assert payload.template_code == "welcome"
        assert payload.priority == 5
        assert payload.request_id is not None
    
    def test_valid_push_notification(self):
        """Test creating valid push notification payload"""
        user_data = UserData(
            name="Jane Smith",
            link="https://example.com/action"
        )
        payload = NotificationPayload(
            notification_type=NotificationType.push,
            user_id="223e4567-e89b-12d3-a456-426614174001",
            template_code="alert",
            variables=user_data,
            priority=1
        )
        assert payload.notification_type == NotificationType.push
        assert payload.priority == 1
    
    def test_priority_validation(self):
        """Test that priority is validated correctly"""
        user_data = UserData(
            name="Test User",
            link="https://example.com"
        )
        with pytest.raises(ValidationError):
            NotificationPayload(
                notification_type=NotificationType.email,
                user_id="123e4567-e89b-12d3-a456-426614174000",
                template_code="test",
                variables=user_data,
                priority=11  # invalid: > 10
            )
    
    def test_missing_required_fields(self):
        """Test that missing required fields raises validation error"""
        with pytest.raises(ValidationError):
            NotificationPayload(notification_type=NotificationType.email)


class TestUserData:
    """Test UserData schema"""
    
    def test_valid_user_data(self):
        """Test creating valid user data"""
        data = UserData(
            name="Test User",
            link="https://example.com",
            meta={"custom": "data"}
        )
        assert data.name == "Test User"
        assert str(data.link) == "https://example.com/"
        assert data.meta == {"custom": "data"}
    
    def test_user_data_without_meta(self):
        """Test user data without optional meta field"""
        data = UserData(
            name="Test User",
            link="https://example.com"
        )
        assert data.meta is None


class TestUserCreate:
    """Test UserCreate schema"""
    
    def test_valid_user_creation(self):
        """Test creating valid user"""
        preferences = UserPreference(email=True, push=True)
        user = UserCreate(
            name="John Doe",
            email="john@example.com",
            push_token="device-token-123",
            preferences=preferences,
            password="securepass123"
        )
        assert user.name == "John Doe"
        assert user.email == "john@example.com"
        assert user.preferences.email is True
        assert user.preferences.push is True
    
    def test_default_preferences(self):
        """Test user with default preferences"""
        user = UserCreate(
            name="Jane Doe",
            email="jane@example.com",
            password="password123"
        )
        assert user.preferences.email is True
        assert user.preferences.push is True
    
    def test_invalid_email(self):
        """Test that invalid email raises validation error"""
        with pytest.raises(ValidationError):
            UserCreate(
                name="Test User",
                email="invalid-email",
                password="password123"
            )


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
