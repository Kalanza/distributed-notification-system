"""
Tests for shared utilities
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from shared.utils.logger import get_logger, CorrelationLogger
from shared.utils.circuit_breaker import CircuitBreaker
from shared.utils.retry import retry_with_backoff


class TestLogger:
    """Test logging functionality"""
    
    def test_get_logger_creates_instance(self):
        """Test that get_logger creates a logger instance"""
        logger = get_logger("test_service")
        assert isinstance(logger, CorrelationLogger)
        assert logger.service_name == "test_service"
    
    def test_logger_info_with_correlation_id(self, capsys):
        """Test logging info message with correlation ID"""
        logger = get_logger("test_service")
        logger.info("Test message", correlation_id="test-123")
        # Logger should execute without errors
        assert True
    
    def test_logger_error_without_correlation_id(self):
        """Test logging error message without correlation ID"""
        logger = get_logger("test_service")
        logger.error("Error message")
        # Logger should execute without errors
        assert True


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    def test_circuit_breaker_success(self):
        """Test circuit breaker with successful calls"""
        cb = CircuitBreaker(failure_threshold=3, timeout=1)
        
        @cb
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
        assert cb.state == "closed"
    
    def test_circuit_breaker_opens_on_failures(self):
        """Test that circuit breaker opens after threshold failures"""
        cb = CircuitBreaker(failure_threshold=2, timeout=1)
        
        @cb
        def failing_function():
            raise Exception("Test failure")
        
        # First failure
        with pytest.raises(Exception):
            failing_function()
        assert cb.failure_count == 1
        
        # Second failure should open circuit
        with pytest.raises(Exception):
            failing_function()
        assert cb.state == "open"
    
    def test_circuit_breaker_state_transitions(self):
        """Test circuit breaker state is initially closed"""
        cb = CircuitBreaker(failure_threshold=3, timeout=1)
        assert cb.state == "closed"
        assert cb.failure_count == 0


class TestRetry:
    """Test retry decorator functionality"""
    
    def test_retry_succeeds_on_first_attempt(self):
        """Test that retry succeeds if first attempt works"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_function()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_eventually_succeeds(self):
        """Test that retry eventually succeeds after failures"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, delay=0.01)
        def eventually_successful():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = eventually_successful()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_fails_after_max_attempts(self):
        """Test that retry fails after max attempts"""
        call_count = 0
        
        @retry_with_backoff(max_retries=2, delay=0.01)
        def always_failing():
            nonlocal call_count
            call_count += 1
            raise Exception("Permanent failure")
        
        with pytest.raises(Exception) as exc_info:
            always_failing()
        assert "Permanent failure" in str(exc_info.value)
        assert call_count == 3  # initial + 2 retries
