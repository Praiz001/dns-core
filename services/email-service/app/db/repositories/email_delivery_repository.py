"""
Email Delivery Repository

Implements repository pattern for email delivery data access.
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime

from app.models.email_delivery import EmailDelivery
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmailDeliveryRepository:
    """Repository for email delivery operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, delivery: EmailDelivery) -> EmailDelivery:
        """Create a new email delivery record."""
        self.session.add(delivery)
        await self.session.flush()
        await self.session.refresh(delivery)
        logger.info(f"Created email delivery record: {delivery.id}")
        return delivery
    
    async def get_by_id(self, delivery_id: UUID) -> Optional[EmailDelivery]:
        """Get email delivery by ID."""
        result = await self.session.execute(
            select(EmailDelivery).where(EmailDelivery.id == delivery_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_notification_id(self, notification_id: UUID) -> Optional[EmailDelivery]:
        """Get email delivery by notification ID."""
        result = await self.session.execute(
            select(EmailDelivery).where(EmailDelivery.notification_id == notification_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_provider_message_id(self, provider_message_id: str) -> Optional[EmailDelivery]:
        """Get email delivery by provider message ID."""
        result = await self.session.execute(
            select(EmailDelivery).where(EmailDelivery.provider_message_id == provider_message_id)
        )
        return result.scalar_one_or_none()
    
    async def update_status(
        self,
        delivery_id: UUID,
        status: str,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        provider_message_id: Optional[str] = None,
    ) -> bool:
        """Update delivery status."""
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow(),
        }
        
        if status == "sent":
            update_data["sent_at"] = datetime.utcnow()
        elif status == "delivered":
            update_data["delivered_at"] = datetime.utcnow()
        elif status == "failed":
            update_data["failed_at"] = datetime.utcnow()
        
        if error_message:
            update_data["error_message"] = error_message
        if error_code:
            update_data["error_code"] = error_code
        if provider_message_id:
            update_data["provider_message_id"] = provider_message_id
        
        result = await self.session.execute(
            update(EmailDelivery)
            .where(EmailDelivery.id == delivery_id)
            .values(**update_data)
        )
        
        await self.session.flush()
        logger.info(f"Updated email delivery {delivery_id} to status: {status}")
        return result.rowcount > 0
    
    async def increment_attempt(self, delivery_id: UUID) -> bool:
        """Increment attempt count."""
        result = await self.session.execute(
            update(EmailDelivery)
            .where(EmailDelivery.id == delivery_id)
            .values(
                attempt_count=EmailDelivery.attempt_count + 1,
                updated_at=datetime.utcnow(),
            )
        )
        await self.session.flush()
        return result.rowcount > 0
    
    async def get_failed_deliveries(self, limit: int = 100) -> List[EmailDelivery]:
        """Get failed deliveries that can be retried."""
        result = await self.session.execute(
            select(EmailDelivery)
            .where(EmailDelivery.status == "failed")
            .where(EmailDelivery.attempt_count < EmailDelivery.max_attempts)
            .limit(limit)
        )
        return list(result.scalars().all())
