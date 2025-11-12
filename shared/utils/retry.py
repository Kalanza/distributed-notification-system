import time
from typing import Callable, Any, Optional, Tuple, Type
from functools import wraps
from shared.utils.logger import get_logger


logger = get_logger("retry_system")


class MaxRetriesExceededException(Exception):
    """Raised when max retry attempts are exceeded"""
    pass


def exponential_backoff(attempt: int, base: int = 2, factor: int = 1) -> int:
    """
    Calculate exponential backoff delay
    
    Formula: factor * (base ** attempt)
    
    Examples:
        attempt 1: 2 seconds
        attempt 2: 4 seconds
        attempt 3: 8 seconds
    """
    return factor * (base ** attempt)


def retry_with_backoff(
    max_attempts: int = 3,
    backoff_base: int = 2,
    backoff_factor: int = 1,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator for retry logic with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_base: Base for exponential backoff calculation
        backoff_factor: Factor to multiply backoff delay
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback function called on each retry
    
    Usage:
        @retry_with_backoff(max_attempts=3, backoff_base=2)
        def send_notification():
            # ... notification logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts - 1:
                        delay = exponential_backoff(attempt + 1, backoff_base, backoff_factor)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}. "
                            f"Retrying in {delay}s. Error: {str(e)}"
                        )
                        
                        if on_retry:
                            on_retry(attempt + 1, e)
                        
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}. "
                            f"Final error: {str(e)}"
                        )
            
            raise MaxRetriesExceededException(
                f"Failed after {max_attempts} attempts. Last error: {str(last_exception)}"
            ) from last_exception
        
        return wrapper
    
    return decorator


class RetryableTask:
    """
    A retryable task that can be queued and retried with backoff
    Used for message queue retry logic
    """
    
    def __init__(
        self,
        task_id: str,
        func: Callable,
        max_attempts: int = 3,
        backoff_base: int = 2,
        backoff_factor: int = 1
    ):
        self.task_id = task_id
        self.func = func
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base
        self.backoff_factor = backoff_factor
        self.attempt_count = 0
    
    def execute(self, *args, **kwargs) -> Any:
        """Execute the task with retry logic"""
        self.attempt_count += 1
        
        if self.attempt_count > self.max_attempts:
            raise MaxRetriesExceededException(
                f"Task {self.task_id} exceeded max attempts ({self.max_attempts})"
            )
        
        try:
            result = self.func(*args, **kwargs)
            logger.info(f"Task {self.task_id} completed successfully on attempt {self.attempt_count}")
            return result
        except Exception as e:
            logger.error(
                f"Task {self.task_id} failed on attempt {self.attempt_count}/{self.max_attempts}. "
                f"Error: {str(e)}"
            )
            raise e
    
    def get_next_retry_delay(self) -> int:
        """Calculate delay before next retry"""
        return exponential_backoff(self.attempt_count, self.backoff_base, self.backoff_factor)
    
    def should_retry(self) -> bool:
        """Check if task should be retried"""
        return self.attempt_count < self.max_attempts
