import logging
import sys
from typing import Optional
from datetime import datetime
import json


class CorrelationLogger:
    """Logger with correlation ID support for distributed tracing"""
    
    def __init__(self, service_name: str, log_level: str = "INFO"):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, log_level.upper()))
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        if not self.logger.handlers:
            self.logger.addHandler(handler)
    
    def _log(self, level: str, message: str, correlation_id: Optional[str] = None, **kwargs):
        """Internal log method with correlation ID"""
        extra = {
            'correlation_id': correlation_id or 'N/A',
            **kwargs
        }
        getattr(self.logger, level)(message, extra=extra)
    
    def info(self, message: str, correlation_id: Optional[str] = None, **kwargs):
        self._log('info', message, correlation_id, **kwargs)
    
    def error(self, message: str, correlation_id: Optional[str] = None, **kwargs):
        self._log('error', message, correlation_id, **kwargs)
    
    def warning(self, message: str, correlation_id: Optional[str] = None, **kwargs):
        self._log('warning', message, correlation_id, **kwargs)
    
    def debug(self, message: str, correlation_id: Optional[str] = None, **kwargs):
        self._log('debug', message, correlation_id, **kwargs)
    
    def log_notification_lifecycle(self, stage: str, request_id: str, correlation_id: str, status: str, **kwargs):
        """Log notification lifecycle events"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'service': self.service_name,
            'stage': stage,
            'request_id': request_id,
            'correlation_id': correlation_id,
            'status': status,
            **kwargs
        }
        self.info(f"Notification lifecycle: {json.dumps(log_entry)}", correlation_id=correlation_id)


def get_logger(service_name: str, log_level: str = "INFO") -> CorrelationLogger:
    """Get or create a logger for a service"""
    return CorrelationLogger(service_name, log_level)
