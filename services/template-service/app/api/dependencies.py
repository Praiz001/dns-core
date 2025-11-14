from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.repositories.template_repository import TemplateRepository
from app.services.template_service import TemplateService
from app.services.render_service import RenderService
from app.utils.redis_client import redis_client


def get_template_repository(db: AsyncSession = Depends(get_db)) -> TemplateRepository:
    """Dependency for template repository"""
    return TemplateRepository(db)


def get_render_service() -> RenderService:
    """Dependency for render service"""
    return RenderService()


def get_template_service(
    repository: TemplateRepository = Depends(get_template_repository),
    render_service: RenderService = Depends(get_render_service)
) -> TemplateService:
    """Dependency for template service"""
    return TemplateService(repository, render_service, redis_client)