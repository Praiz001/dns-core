"""
Circuit Breaker implementation for failure handling.

Prevents cascading failures by temporarily blocking calls to failing services.
"""

from datetime import datetime, timedelta
from typing import Callable, Any
from enum import Enum

from app.utils.logger import get_logger

logger = get_logger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Blocking calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents cascading failures by temporarily blocking calls to failing services.
    After a timeout, allows a test call to check if the service has recovered.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        name: str = "default"
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting recovery (half-open state)
            name: Name for logging purposes
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.name = name
        
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = CircuitBreakerState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit breaker is in OPEN state."""
        return self.state == CircuitBreakerState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return False
        
        return datetime.utcnow() >= self.last_failure_time + timedelta(seconds=self.timeout)
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
        """
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Service unavailable."
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise e
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute async function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
        """
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Service unavailable."
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.info(f"Circuit breaker '{self.name}' recovered, entering CLOSED state")
        
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            logger.warning(
                f"Circuit breaker '{self.name}' threshold reached "
                f"({self.failure_count} failures), entering OPEN state"
            )
            self.state = CircuitBreakerState.OPEN
    
    def reset(self):
        """Manually reset circuit breaker."""
        logger.info(f"Circuit breaker '{self.name}' manually reset")
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    def record_success(self):
        """Publicly record a successful operation."""
        self._on_success()
    
    def record_failure(self):
        """Publicly record a failed operation."""
        self._on_failure()
