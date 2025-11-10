from pydantic import BaseModel
from typing import Optional

class NotificationPayload(BaseModel):
    request_id: str
    user_id: int
    channel: str  # "email" or "push"
    template_id: str
    variables: dict
    timestamp: Optional[str] = None
