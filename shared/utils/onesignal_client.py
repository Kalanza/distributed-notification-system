"""
OneSignal Client for Push Notifications
Handles sending push notifications via OneSignal REST API
"""

import httpx
from typing import Dict, List, Optional, Any
from shared.config.settings import settings
from shared.utils.logger import get_logger
from shared.utils.circuit_breaker import circuit_breaker
from shared.utils.retry import retry_with_backoff

logger = get_logger("onesignal_client", settings.LOG_LEVEL)


class OneSignalClient:
    """Client for OneSignal Push Notification API"""
    
    def __init__(self):
        self.app_id = settings.ONESIGNAL_APP_ID
        self.rest_api_key = settings.ONESIGNAL_REST_API_KEY
        self.base_url = "https://onesignal.com/api/v1"
        self.headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Basic {self.rest_api_key}"
        }
    
    @circuit_breaker(failure_threshold=5, recovery_timeout=60, name="onesignal_send")
    @retry_with_backoff(max_attempts=3, backoff_base=2)
    async def send_notification(
        self,
        player_ids: List[str],
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        url: Optional[str] = None,
        image_url: Optional[str] = None,
        buttons: Optional[List[Dict[str, str]]] = None,
        priority: int = 10
    ) -> Dict[str, Any]:
        """
        Send push notification via OneSignal
        
        Args:
            player_ids: List of OneSignal player IDs (device tokens)
            title: Notification title
            message: Notification message body
            data: Additional data payload
            url: URL to open when notification is clicked
            image_url: Large image URL for rich notifications
            buttons: Action buttons [{"id": "id1", "text": "Button 1"}]
            priority: Notification priority (1-10, 10 is highest)
        
        Returns:
            OneSignal API response
        """
        try:
            payload = {
                "app_id": self.app_id,
                "include_player_ids": player_ids,
                "headings": {"en": title},
                "contents": {"en": message},
                "priority": priority
            }
            
            # Add optional fields
            if data:
                payload["data"] = data
            
            if url:
                payload["url"] = url
            
            if image_url:
                payload["big_picture"] = image_url
                payload["large_icon"] = image_url
            
            if buttons:
                payload["buttons"] = buttons
            
            # Send notification
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/notifications",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(
                    f"OneSignal notification sent successfully. "
                    f"Recipients: {result.get('recipients', 0)}, "
                    f"ID: {result.get('id', 'N/A')}"
                )
                
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"OneSignal API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to send OneSignal notification: {str(e)}")
            raise
    
    @retry_with_backoff(max_attempts=3, backoff_base=2)
    async def send_to_segments(
        self,
        segments: List[str],
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        url: Optional[str] = None,
        filters: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Send notification to user segments
        
        Args:
            segments: List of segment names (e.g., ["Active Users", "Subscribed Users"])
            title: Notification title
            message: Notification message
            data: Additional data
            url: URL to open
            filters: Advanced filters for targeting
        
        Returns:
            OneSignal API response
        """
        try:
            payload = {
                "app_id": self.app_id,
                "included_segments": segments,
                "headings": {"en": title},
                "contents": {"en": message}
            }
            
            if data:
                payload["data"] = data
            
            if url:
                payload["url"] = url
            
            if filters:
                payload["filters"] = filters
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/notifications",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(
                    f"OneSignal segment notification sent. "
                    f"Segments: {segments}, "
                    f"ID: {result.get('id', 'N/A')}"
                )
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to send segment notification: {str(e)}")
            raise
    
    @retry_with_backoff(max_attempts=3, backoff_base=2)
    async def create_player(
        self,
        device_type: int,
        identifier: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
        external_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create/update a player (device) in OneSignal
        
        Args:
            device_type: Device type (1=iOS, 2=Android, 5=Web Push)
            identifier: Push token from device
            tags: User tags for segmentation
            external_user_id: Your internal user ID
        
        Returns:
            OneSignal player creation response with player_id
        """
        try:
            payload = {
                "app_id": self.app_id,
                "device_type": device_type
            }
            
            if identifier:
                payload["identifier"] = identifier
            
            if tags:
                payload["tags"] = tags
            
            if external_user_id:
                payload["external_user_id"] = external_user_id
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/players",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"OneSignal player created: {result.get('id', 'N/A')}")
                return result
                
        except Exception as e:
            logger.error(f"Failed to create OneSignal player: {str(e)}")
            raise
    
    @retry_with_backoff(max_attempts=3, backoff_base=2)
    async def cancel_notification(self, notification_id: str) -> Dict[str, Any]:
        """
        Cancel a scheduled notification
        
        Args:
            notification_id: OneSignal notification ID
        
        Returns:
            Cancellation response
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"{self.base_url}/notifications/{notification_id}?app_id={self.app_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"OneSignal notification {notification_id} cancelled")
                return result
                
        except Exception as e:
            logger.error(f"Failed to cancel notification {notification_id}: {str(e)}")
            raise
    
    @retry_with_backoff(max_attempts=3, backoff_base=2)
    async def get_notification_status(self, notification_id: str) -> Dict[str, Any]:
        """
        Get notification delivery status
        
        Args:
            notification_id: OneSignal notification ID
        
        Returns:
            Notification status and statistics
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/notifications/{notification_id}?app_id={self.app_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(
                    f"OneSignal notification {notification_id} status: "
                    f"Sent: {result.get('successful', 0)}, "
                    f"Failed: {result.get('failed', 0)}, "
                    f"Converted: {result.get('converted', 0)}"
                )
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get notification status: {str(e)}")
            raise


# Singleton instance
_onesignal_client: Optional[OneSignalClient] = None


def get_onesignal_client() -> OneSignalClient:
    """Get OneSignal client singleton"""
    global _onesignal_client
    if _onesignal_client is None:
        _onesignal_client = OneSignalClient()
    return _onesignal_client
