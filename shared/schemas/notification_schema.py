from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, Literal
from datetime import datetime
import uuid


class NotificationPayload(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request ID for idempotency")
    user_id: int = Field(..., description="User ID to send notification to")
    channel: Literal["email", "push"] = Field(..., description="Notification channel: email or push")
    template_id: str = Field(..., description="Template ID to use for the notification")
    variables: Dict[str, Any] = Field(default_factory=dict, description="Variables to substitute in template")
    timestamp: Optional[str] = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Timestamp of the request")
    priority: Optional[Literal["high", "medium", "low"]] = Field(default="medium", description="Notification priority")
    correlation_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Correlation ID for tracking")
    
    @validator('channel')
    def validate_channel(cls, v):
        if v not in ["email", "push"]:
            raise ValueError("Channel must be 'email' or 'push'")
        return v


class NotificationStatus(BaseModel):
    request_id: str
    user_id: int
    channel: str
    status: Literal["pending", "queued", "processing", "sent", "failed", "retry"]
    created_at: str
    updated_at: str
    error_message: Optional[str] = None
    retry_count: int = 0
    delivered_at: Optional[str] = None


class EmailNotification(BaseModel):
    to_email: str
    subject: str
    body_html: str
    body_text: Optional[str] = None
    from_email: Optional[str] = None
    reply_to: Optional[str] = None


class PushNotification(BaseModel):
    device_token: str
    title: str
    body: str
    image_url: Optional[str] = None
    action_url: Optional[str] = None
    badge: Optional[int] = None
    sound: Optional[str] = "default"
    data: Optional[Dict[str, Any]] = None
