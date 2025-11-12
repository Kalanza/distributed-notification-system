import os
from typing import Optional
from urllib.parse import urlparse


class Settings:
    # RabbitMQ Configuration - Support CloudAMQP URL format
    def _parse_rabbitmq_url(self):
        """Parse CloudAMQP URL or use individual env vars"""
        cloudamqp_url = os.getenv("CLOUDAMQP_URL") or os.getenv("RABBITMQ_URL")
        if cloudamqp_url:
            parsed = urlparse(cloudamqp_url)
            return {
                "host": parsed.hostname or "localhost",
                "port": parsed.port or 5672,
                "user": parsed.username or "guest",
                "pass": parsed.password or "guest"
            }
        return {
            "host": os.getenv("RABBITMQ_HOST", "localhost"),
            "port": int(os.getenv("RABBITMQ_PORT", "5672")),
            "user": os.getenv("RABBITMQ_USER", "guest"),
            "pass": os.getenv("RABBITMQ_PASS", "guest")
        }
    
    _rabbitmq_config = None
    
    @property
    def RABBITMQ_HOST(self) -> str:
        if not self._rabbitmq_config:
            self._rabbitmq_config = self._parse_rabbitmq_url()
        return self._rabbitmq_config["host"]
    
    @property
    def RABBITMQ_PORT(self) -> int:
        if not self._rabbitmq_config:
            self._rabbitmq_config = self._parse_rabbitmq_url()
        return self._rabbitmq_config["port"]
    
    @property
    def RABBITMQ_USER(self) -> str:
        if not self._rabbitmq_config:
            self._rabbitmq_config = self._parse_rabbitmq_url()
        return self._rabbitmq_config["user"]
    
    @property
    def RABBITMQ_PASS(self) -> str:
        if not self._rabbitmq_config:
            self._rabbitmq_config = self._parse_rabbitmq_url()
        return self._rabbitmq_config["pass"]
    
    RABBITMQ_EXCHANGE: str = "notifications.direct"
    
    # Redis Configuration - Support Heroku Redis URL format
    def _parse_redis_url(self):
        """Parse Heroku Redis URL or use individual env vars"""
        redis_url = os.getenv("REDIS_URL") or os.getenv("REDIS_TLS_URL")
        if redis_url:
            parsed = urlparse(redis_url)
            return {
                "host": parsed.hostname or "localhost",
                "port": parsed.port or 6379,
                "db": 0,
                "password": parsed.password,
                "ssl": redis_url.startswith("rediss://")
            }
        return {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", "6379")),
            "db": int(os.getenv("REDIS_DB", "0")),
            "password": None,
            "ssl": False
        }
    
    _redis_config = None
    
    @property
    def REDIS_HOST(self) -> str:
        if not self._redis_config:
            self._redis_config = self._parse_redis_url()
        return self._redis_config["host"]
    
    @property
    def REDIS_PORT(self) -> int:
        if not self._redis_config:
            self._redis_config = self._parse_redis_url()
        return self._redis_config["port"]
    
    @property
    def REDIS_DB(self) -> int:
        if not self._redis_config:
            self._redis_config = self._parse_redis_url()
        return self._redis_config["db"]
    
    @property
    def REDIS_PASSWORD(self) -> Optional[str]:
        if not self._redis_config:
            self._redis_config = self._parse_redis_url()
        return self._redis_config.get("password")
    
    @property
    def REDIS_SSL(self) -> bool:
        if not self._redis_config:
            self._redis_config = self._parse_redis_url()
        return self._redis_config.get("ssl", False)
    
    # Database Configuration - Support Heroku Postgres URL format
    def _parse_database_url(self):
        """Parse Heroku DATABASE_URL or use individual env vars"""
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            # Heroku provides postgres:// but SQLAlchemy needs postgresql://
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            
            parsed = urlparse(database_url)
            return {
                "host": parsed.hostname or "localhost",
                "port": parsed.port or 5432,
                "name": parsed.path[1:] if parsed.path else "notification_db",
                "user": parsed.username or "postgres",
                "pass": parsed.password or "password"
            }
        return {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "name": os.getenv("DB_NAME", "notification_db"),
            "user": os.getenv("DB_USER", "postgres"),
            "pass": os.getenv("DB_PASS", "password")
        }
    
    _db_config = None
    
    @property
    def DB_HOST(self) -> str:
        if not self._db_config:
            self._db_config = self._parse_database_url()
        return self._db_config["host"]
    
    @property
    def DB_PORT(self) -> int:
        if not self._db_config:
            self._db_config = self._parse_database_url()
        return self._db_config["port"]
    
    @property
    def DB_NAME(self) -> str:
        if not self._db_config:
            self._db_config = self._parse_database_url()
        return self._db_config["name"]
    
    @property
    def DB_USER(self) -> str:
        if not self._db_config:
            self._db_config = self._parse_database_url()
        return self._db_config["user"]
    
    @property
    def DB_PASS(self) -> str:
        if not self._db_config:
            self._db_config = self._parse_database_url()
        return self._db_config["pass"]
    
    # Service Configuration
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "notification-service")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Circuit Breaker Configuration
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = int(os.getenv("CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "60"))
    CIRCUIT_BREAKER_EXPECTED_EXCEPTION: tuple = (Exception,)
    
    # Retry Configuration
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    RETRY_BACKOFF_BASE: int = int(os.getenv("RETRY_BACKOFF_BASE", "2"))
    RETRY_BACKOFF_FACTOR: int = int(os.getenv("RETRY_BACKOFF_FACTOR", "1"))
    
    # JWT Configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_MINUTES: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))
    
    # Email Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@notifications.com")
    
    # OneSignal Configuration (Push Notifications)
    ONESIGNAL_APP_ID: Optional[str] = os.getenv("ONESIGNAL_APP_ID", None)
    ONESIGNAL_REST_API_KEY: Optional[str] = os.getenv("ONESIGNAL_REST_API_KEY", None)
    ONESIGNAL_API_URL: str = "https://onesignal.com/api/v1/notifications"
    
    # Rate Limiting
    RATE_LIMIT_PER_USER: int = int(os.getenv("RATE_LIMIT_PER_USER", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    
    @property
    def database_url(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
