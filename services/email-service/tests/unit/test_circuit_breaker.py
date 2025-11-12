"""
Unit tests for Circuit Breaker utility.

Tests cover:
- Circuit breaker states (closed, open, half-open)
- Failure threshold triggering
- Timeout and recovery
- Success tracking
- Async and sync call support
"""

import pytest
from unittest.mock import Mock, AsyncMock
import time
from datetime import datetime, timedelta

from app.utils.circuit_breaker import CircuitBreaker, CircuitBreakerError, CircuitBreakerState


class TestCircuitBreaker:
    """Test suite for circuit breaker."""
    
    def test_initial_state_closed(self):
        """Test circuit breaker starts in closed state."""
        cb = CircuitBreaker(
            failure_threshold=5,
            timeout=60,
            name="test-cb"
        )
        
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.is_open is False
    
    def test_record_success_resets_failures(self):
        """Test that recording success resets failure count."""
        cb = CircuitBreaker(failure_threshold=5, timeout=60)
        
        # Record some failures
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2
        
        # Record success should reset
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitBreakerState.CLOSED
    
    def test_failure_threshold_opens_circuit(self):
        """Test circuit opens after reaching failure threshold."""
        cb = CircuitBreaker(failure_threshold=3, timeout=60)
        
        # Record failures up to threshold
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED
        
        # One more failure should open circuit
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.is_open is True
    
    def test_open_circuit_rejects_calls(self):
        """Test that open circuit rejects calls."""
        cb = CircuitBreaker(failure_threshold=2, timeout=60)
        
        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is True
        
        # Calling should raise error
        def test_func():
            return "success"
        
        with pytest.raises(CircuitBreakerError) as exc_info:
            cb.call(test_func)
        
        assert "Circuit breaker 'default' is OPEN" in str(exc_info.value)
    
    def test_circuit_transitions_to_half_open_after_timeout(self):
        """Test circuit moves to half-open state after timeout."""
        cb = CircuitBreaker(failure_threshold=2, timeout=1)  # 1 second timeout
        
        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        
        # Wait for timeout
        time.sleep(1.1)
        
        # Next call should transition to half-open
        def test_func():
            return "success"
        
        result = cb.call(test_func)
        
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED  # Successful call closes it
    
    def test_half_open_success_closes_circuit(self):
        """Test successful call in half-open state closes circuit."""
        cb = CircuitBreaker(failure_threshold=2, timeout=1)
        
        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        
        # Wait for timeout and transition to half-open
        time.sleep(1.1)
        
        # Successful call should close circuit
        def test_func():
            return "success"
        
        result = cb.call(test_func)
        
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
    
    def test_half_open_failure_reopens_circuit(self):
        """Test failed call in half-open state reopens circuit."""
        cb = CircuitBreaker(failure_threshold=2, timeout=1)
        
        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        
        # Wait for timeout
        time.sleep(1.1)
        
        # Failing call should reopen circuit
        def test_func():
            raise Exception("Test error")
        
        with pytest.raises(Exception):
            cb.call(test_func)
        
        assert cb.state == CircuitBreakerState.OPEN
    
    def test_call_with_successful_function(self):
        """Test calling function through closed circuit breaker."""
        cb = CircuitBreaker(failure_threshold=5, timeout=60)
        
        def test_func():
            return "success"
        
        result = cb.call(test_func)
        
        assert result == "success"
        assert cb.failure_count == 0
        assert cb.state == CircuitBreakerState.CLOSED
    
    def test_call_with_failing_function(self):
        """Test calling failing function increments failure count."""
        cb = CircuitBreaker(failure_threshold=5, timeout=60)
        
        def test_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            cb.call(test_func)
        
        assert cb.failure_count == 1
        assert cb.state == CircuitBreakerState.CLOSED  # Not reached threshold yet
    
    def test_call_with_args_and_kwargs(self):
        """Test calling function with arguments."""
        cb = CircuitBreaker(failure_threshold=5, timeout=60)
        
        def test_func(a, b, c=None):
            return f"{a}-{b}-{c}"
        
        result = cb.call(test_func, 1, 2, c=3)
        
        assert result == "1-2-3"
    
    @pytest.mark.asyncio
    async def test_call_async_with_successful_function(self):
        """Test calling async function through circuit breaker."""
        cb = CircuitBreaker(failure_threshold=5, timeout=60)
        
        async def test_func():
            return "async success"
        
        result = await cb.call_async(test_func)
        
        assert result == "async success"
        assert cb.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_call_async_with_failing_function(self):
        """Test calling failing async function."""
        cb = CircuitBreaker(failure_threshold=5, timeout=60)
        
        async def test_func():
            raise ValueError("Async test error")
        
        with pytest.raises(ValueError):
            await cb.call_async(test_func)
        
        assert cb.failure_count == 1
    
    @pytest.mark.asyncio
    async def test_call_async_open_circuit(self):
        """Test async call rejected when circuit is open."""
        cb = CircuitBreaker(failure_threshold=2, timeout=60)
        
        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        
        async def test_func():
            return "success"
        
        with pytest.raises(CircuitBreakerError):
            await cb.call_async(test_func)
    
    @pytest.mark.asyncio
    async def test_call_async_with_args_and_kwargs(self):
        """Test calling async function with arguments."""
        cb = CircuitBreaker(failure_threshold=5, timeout=60)
        
        async def test_func(a, b, c=None):
            return f"{a}-{b}-{c}"
        
        result = await cb.call_async(test_func, 1, 2, c=3)
        
        assert result == "1-2-3"
    
    def test_multiple_failures_before_threshold(self):
        """Test multiple failures without reaching threshold."""
        cb = CircuitBreaker(failure_threshold=5, timeout=60)
        
        for i in range(4):
            cb.record_failure()
            assert cb.state == CircuitBreakerState.CLOSED
        
        assert cb.failure_count == 4
        assert cb.is_open is False
    
    def test_circuit_breaker_name(self):
        """Test circuit breaker name is set correctly."""
        cb = CircuitBreaker(
            failure_threshold=5,
            timeout=60,
            name="my-service"
        )
        
        assert cb.name == "my-service"
    
    def test_timeout_configuration(self):
        """Test timeout is configured correctly."""
        cb = CircuitBreaker(failure_threshold=5, timeout=120)
        
        assert cb.timeout == 120
    
    def test_failure_threshold_configuration(self):
        """Test failure threshold is configured correctly."""
        cb = CircuitBreaker(failure_threshold=10, timeout=60)
        
        assert cb.failure_threshold == 10
    
    def test_last_failure_time_updated(self):
        """Test last failure time is updated on failure."""
        cb = CircuitBreaker(failure_threshold=5, timeout=60)
        
        before = datetime.utcnow()
        cb.record_failure()
        after = datetime.utcnow()
        
        assert cb.last_failure_time is not None
        # Should be between before and after
        assert before <= cb.last_failure_time <= after
    
    def test_concurrent_failures(self):
        """Test handling of rapid concurrent failures."""
        cb = CircuitBreaker(failure_threshold=3, timeout=60)
        
        # Simulate rapid failures
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.failure_count == 3
    
    @pytest.mark.asyncio
    async def test_circuit_recovery_workflow(self):
        """Test complete circuit breaker recovery workflow."""
        cb = CircuitBreaker(failure_threshold=2, timeout=1)
        
        # 1. Circuit is closed initially
        assert cb.state == CircuitBreakerState.CLOSED
        
        # 2. Failures open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        
        # 3. Wait for timeout
        time.sleep(1.1)
        
        # 4. Successful call closes circuit
        async def test_func():
            return "success"
        
        result = await cb.call_async(test_func)
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
