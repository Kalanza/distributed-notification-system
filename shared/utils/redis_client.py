import redis
from typing import Optional, Any
import json
from shared.config.settings import settings
from shared.utils.logger import get_logger


logger = get_logger("redis_client")


class RedisClient:
    """Redis client for caching and rate limiting"""
    
    def __init__(self):
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting key {key} from Redis: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set value in Redis with optional expiration"""
        try:
            serialized = json.dumps(value)
            if expire:
                self.client.setex(key, expire, serialized)
            else:
                self.client.set(key, serialized)
            return True
        except Exception as e:
            logger.error(f"Error setting key {key} in Redis: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting key {key} from Redis: {str(e)}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter in Redis"""
        try:
            return self.client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing key {key} in Redis: {str(e)}")
            return 0
    
    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key"""
        try:
            self.client.expire(key, seconds)
            return True
        except Exception as e:
            logger.error(f"Error setting expiration on key {key}: {str(e)}")
            return False
    
    def check_rate_limit(self, user_id: int, limit: int, window: int) -> tuple[bool, int]:
        """
        Check if user has exceeded rate limit
        
        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        key = f"rate_limit:user:{user_id}"
        try:
            current = self.client.get(key)
            
            if current is None:
                # First request in window
                self.client.setex(key, window, 1)
                return True, limit - 1
            
            current_count = int(current)
            
            if current_count >= limit:
                return False, 0
            
            # Increment counter
            new_count = self.client.incr(key)
            return True, limit - new_count
        except Exception as e:
            logger.error(f"Error checking rate limit for user {user_id}: {str(e)}")
            # Fail open - allow request if Redis is down
            return True, limit
    
    def cache_user_preferences(self, user_id: int, preferences: dict, expire: int = 300):
        """Cache user preferences for quick access"""
        key = f"user:preferences:{user_id}"
        self.set(key, preferences, expire)
    
    def get_cached_user_preferences(self, user_id: int) -> Optional[dict]:
        """Get cached user preferences"""
        key = f"user:preferences:{user_id}"
        return self.get(key)
    
    def mark_notification_processed(self, request_id: str, expire: int = 3600):
        """Mark notification as processed for idempotency"""
        key = f"notification:processed:{request_id}"
        self.set(key, {"processed": True, "timestamp": str(time.time())}, expire)
    
    def is_notification_processed(self, request_id: str) -> bool:
        """Check if notification was already processed"""
        key = f"notification:processed:{request_id}"
        return self.get(key) is not None
    
    def health_check(self) -> bool:
        """Check if Redis is healthy"""
        try:
            self.client.ping()
            return True
        except Exception:
            return False


# Import time for timestamp
import time


def get_redis_client() -> RedisClient:
    """Get Redis client instance"""
    return RedisClient()
