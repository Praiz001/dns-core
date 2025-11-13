"""
Dependency injection for FastAPI routes.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.session import get_db
from app.db.repositories.email_delivery_repository import EmailDeliveryRepository
from app.services.external_api import ExternalAPIClient
from app.services.email_service import EmailService


async def get_email_delivery_repository(
    db: AsyncSession = Depends(get_db)
) -> EmailDeliveryRepository:
    """Provide email delivery repository."""
    return EmailDeliveryRepository(db)


async def get_external_api_client() -> ExternalAPIClient:
    """Provide external API client."""
    return ExternalAPIClient()


async def get_email_service(
    repository: EmailDeliveryRepository = Depends(get_email_delivery_repository),
    api_client: ExternalAPIClient = Depends(get_external_api_client)
) -> EmailService:
    """Provide email service."""
    return EmailService(repository, api_client)
