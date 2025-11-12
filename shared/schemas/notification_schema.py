from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class NotificationType(str, Enum):
    """Notification channel types"""
    email = "email"
    push = "push"


class NotificationStatus(str, Enum):
    """Notification delivery status"""
    delivered = "delivered"
    pending = "pending"
    failed = "failed"


class UserData(BaseModel):
    """User data for template variables"""
    name: str = Field(..., description="User's name")
    link: HttpUrl = Field(..., description="Action URL for the notification")
    meta: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class NotificationPayload(BaseModel):
    """Request payload for sending notifications"""
    notification_type: NotificationType = Field(..., description="Type of notification: email or push")
    user_id: str = Field(..., description="User UUID")
    template_code: str = Field(..., description="Template code or path")
    variables: UserData = Field(..., description="Template variables with user data")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request ID for idempotency")
    priority: int = Field(default=5, ge=1, le=10, description="Priority level (1-10, lower is higher priority)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class NotificationStatusUpdate(BaseModel):
    """Status update for a notification"""
    notification_id: str = Field(..., description="Notification ID")
    status: NotificationStatus = Field(..., description="Current status of the notification")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Timestamp of status update")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class UserPreference(BaseModel):
    """User notification preferences"""
    email: bool = Field(default=True, description="Email notifications enabled")
    push: bool = Field(default=True, description="Push notifications enabled")


class UserCreate(BaseModel):
    """Request payload for creating a user"""
    name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    push_token: Optional[str] = Field(default=None, description="Push notification token")
    preferences: UserPreference = Field(default_factory=UserPreference, description="Notification preferences")
    password: str = Field(..., min_length=8, description="User password")


class UserResponse(BaseModel):
    """User response schema"""
    user_id: str = Field(..., description="User UUID")
    name: str
    email: EmailStr
    push_token: Optional[str] = None
    preferences: UserPreference
    created_at: datetime


class EmailNotification(BaseModel):
    """Email notification details"""
    to_email: str
    subject: str
    body_html: str
    body_text: Optional[str] = None
    from_email: Optional[str] = None
    reply_to: Optional[str] = None


class PushNotification(BaseModel):
    """Push notification details"""
    device_token: str
    title: str
    body: str
    image_url: Optional[str] = None
    action_url: Optional[str] = None
    badge: Optional[int] = None
    sound: Optional[str] = "default"
    data: Optional[Dict[str, Any]] = None

