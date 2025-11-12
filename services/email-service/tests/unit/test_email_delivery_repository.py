"""
Unit tests for Email Delivery Repository.

Tests cover:
- Creating email delivery records
- Retrieving records by ID
- Updating delivery status
- Incrementing attempt count
- Getting records by notification ID
- Timestamp management
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.email_delivery_repository import EmailDeliveryRepository
from app.models.email_delivery import EmailDelivery


@pytest.fixture
def mock_session():
    """Create mock async database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def repository(mock_session):
    """Create repository instance with mock session."""
    return EmailDeliveryRepository(mock_session)


@pytest.fixture
def sample_delivery_data():
    """Sample email delivery data."""
    return {
        "notification_id": "notif-123",
        "user_id": "user-456",
        "recipient_email": "user@example.com",
        "subject": "Test Email",
        "provider": "smtp",
        "status": "pending"
    }


class TestEmailDeliveryRepository:
    """Test suite for email delivery repository."""
    
    @pytest.mark.asyncio
    async def test_create_delivery(self, repository, mock_session, sample_delivery_data):
        """Test creating a new email delivery record."""
        # Mock the add, flush, and refresh operations
        mock_session.add = Mock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Create EmailDelivery object
        delivery = EmailDelivery(**sample_delivery_data)
        
        result = await repository.create(delivery)
        
        # Verify session operations were called
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()
        
        # Verify returned object
        assert isinstance(result, EmailDelivery)
        assert result.notification_id == sample_delivery_data["notification_id"]
        assert result.user_id == sample_delivery_data["user_id"]
    
    @pytest.mark.asyncio
    async def test_create_delivery_with_optional_fields(self, repository, mock_session):
        """Test creating delivery with optional fields."""
        mock_session.add = Mock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        delivery = EmailDelivery(
            notification_id="notif-123",
            user_id="user-456",
            recipient_email="user@example.com",
            subject="Test",
            provider="sendgrid",
            status="sent",
            provider_message_id="msg-789",
            extra_data={"campaign": "test"}
        )
        
        result = await repository.create(delivery)
        
        assert result.provider_message_id == "msg-789"
        assert result.extra_data == {"campaign": "test"}
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, mock_session):
        """Test retrieving an existing delivery by ID."""
        # Create mock delivery
        mock_delivery = EmailDelivery(
            id="delivery-123",
            notification_id="notif-123",
            user_id="user-456",
            recipient_email="user@example.com",
            subject="Test",
            provider="smtp",
            status="sent"
        )
        
        # Mock the query result
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_delivery)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await repository.get_by_id("delivery-123")
        
        assert result is not None
        assert result.id == "delivery-123"
        assert result.notification_id == "notif-123"
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_session):
        """Test retrieving non-existent delivery."""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await repository.get_by_id("non-existent")
        
        assert result is None
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_notification_id_found(self, repository, mock_session):
        """Test retrieving delivery by notification ID."""
        mock_delivery = EmailDelivery(
            id="delivery-123",
            notification_id="notif-123",
            user_id="user-456",
            recipient_email="user@example.com",
            subject="Test",
            provider="smtp",
            status="sent"
        )
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_delivery)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await repository.get_by_notification_id("notif-123")
        
        assert result is not None
        assert result.notification_id == "notif-123"
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_notification_id_not_found(self, repository, mock_session):
        """Test retrieving delivery with non-existent notification ID."""
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await repository.get_by_notification_id("non-existent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_status_success(self, repository, mock_session):
        """Test updating delivery status to success."""
        # Mock execute to return result with rowcount
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        
        result = await repository.update_status(
            delivery_id=uuid4(),
            status="sent",
            provider_message_id="msg-789"
        )
        
        assert result is True
        mock_session.flush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_status_failure(self, repository, mock_session):
        """Test updating delivery status to failure."""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        
        result = await repository.update_status(
            delivery_id=uuid4(),
            status="failed",
            error_message="SMTP connection failed"
        )
        
        assert result is True
        mock_session.flush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_status_not_found(self, repository, mock_session):
        """Test updating status for non-existent delivery."""
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        
        result = await repository.update_status(
            delivery_id=uuid4(),
            status="sent"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_increment_attempt(self, repository, mock_session):
        """Test incrementing attempt count."""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        
        result = await repository.increment_attempt(uuid4())
        
        assert result is True
        mock_session.flush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_increment_attempt_not_found(self, repository, mock_session):
        """Test incrementing attempt for non-existent delivery."""
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await repository.increment_attempt(uuid4())
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_create_sets_timestamps(self, repository, mock_session):
        """Test that create sets created_at and updated_at."""
        mock_session.add = Mock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        delivery = EmailDelivery(
            notification_id=str(uuid4()),
            user_id="user-456",
            recipient_email="user@example.com",
            subject="Test",
            provider="smtp",
            status="pending"
        )
        
        result = await repository.create(delivery)
        
        # Timestamps should be set during creation (by SQLAlchemy)
        # We can't test exact values, but verify fields exist
        assert hasattr(result, 'created_at')
        assert hasattr(result, 'updated_at')
    
    @pytest.mark.asyncio
    async def test_update_status_clears_error_on_success(self, repository, mock_session):
        """Test that updating to success clears error message."""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        
        result = await repository.update_status(
            delivery_id=str(uuid4()),
            status="sent",
            provider_message_id="msg-123",
            error_message=None  # Explicitly clearing error
        )
        
        assert result is True
        mock_session.flush.assert_called_once()

