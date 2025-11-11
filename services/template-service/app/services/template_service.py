from typing import Optional, List
from uuid import UUID
import json

from app.db.repositories.template_repository import TemplateRepository
from app.services.render_service import RenderService
from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateResponse, RenderResponse
from app.utils.redis_client import RedisClient


class TemplateService:
    """Service for template business logic"""
    
    def __init__(self, repository: TemplateRepository, render_service: RenderService, redis_client: Optional[RedisClient] = None):
        self.repository = repository
        self.render_service = render_service
        self.redis_client = redis_client
    
    async def create_template(self, template_data: TemplateCreate) -> TemplateResponse:
        """Create a new template"""
        
        # Auto-extract variables from templates if not provided
        if not template_data.variables:
            subject_vars = self.render_service.extract_variables(template_data.subject)
            html_vars = self.render_service.extract_variables(template_data.body_html)
            text_vars = self.render_service.extract_variables(template_data.body_text)
            
            # Combine and deduplicate
            all_vars = set(subject_vars + html_vars + text_vars)
            template_data.variables = list(all_vars)
        
        # Create template in database
        template = await self.repository.create(template_data)
        
        # Invalidate cache for template list
        if self.redis_client:
            await self.redis_client.delete_pattern("templates:list:*")
        
        return TemplateResponse.model_validate(template)
    
    async def get_template(self, template_id: UUID) -> Optional[TemplateResponse]:
        """Get template by ID with caching"""
        
        # Try cache first
        if self.redis_client:
            cache_key = f"templates:id:{template_id}"
            cached = await self.redis_client.get(cache_key)
            
            if cached:
                return TemplateResponse.model_validate_json(cached)
        
        # Get from database
        template = await self.repository.get_by_id(template_id)
        
        if not template:
            return None
        
        response = TemplateResponse.model_validate(template)
        
        # Cache the result
        if self.redis_client:
            await self.redis_client.set(
                cache_key,
                response.model_dump_json(),
                ttl=3600  # 1 hour
            )
        
        return response
    
    async def get_template_by_name(self, name: str) -> Optional[TemplateResponse]:
        """Get template by name with caching"""
        
        # Try cache first
        if self.redis_client:
            cache_key = f"templates:name:{name}"
            cached = await self.redis_client.get(cache_key)
            
            if cached:
                return TemplateResponse.model_validate_json(cached)
        
        # Get from database
        template = await self.repository.get_by_name(name)
        
        if not template:
            return None
        
        response = TemplateResponse.model_validate(template)
        
        # Cache the result
        if self.redis_client:
            await self.redis_client.set(
                cache_key,
                response.model_dump_json(),
                ttl=3600
            )
        
        return response
    
    async def get_templates(
        self,
        skip: int = 0,
        limit: int = 10,
        template_type: Optional[str] = None,
        language: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> tuple[List[TemplateResponse], int]:
        """Get paginated list of templates"""
        
        templates, total = await self.repository.get_all(
            skip=skip,
            limit=limit,
            template_type=template_type,
            language=language,
            is_active=is_active
        )
        
        template_responses = [TemplateResponse.model_validate(t) for t in templates]
        
        return template_responses, total
    
    async def update_template(
        self,
        template_id: UUID,
        template_data: TemplateUpdate
    ) -> Optional[TemplateResponse]:
        """Update template"""
        
        template = await self.repository.update(template_id, template_data)
        
        if not template:
            return None
        
        # Invalidate cache
        if self.redis_client:
            await self.redis_client.delete(f"templates:id:{template_id}")
            await self.redis_client.delete(f"templates:name:{template.name}")
            await self.redis_client.delete_pattern("templates:list:*")
        
        return TemplateResponse.model_validate(template)
    
    async def delete_template(self, template_id: UUID) -> bool:
        """Delete template (soft delete)"""
        
        template = await self.repository.soft_delete(template_id)
        
        if not template:
            return False
        
        # Invalidate cache
        if self.redis_client:
            await self.redis_client.delete(f"templates:id:{template_id}")
            await self.redis_client.delete(f"templates:name:{template.name}")
            await self.redis_client.delete_pattern("templates:list:*")
        
        return True
    
    async def render_template(
        self,
        template_id: UUID,
        variables: dict
    ) -> RenderResponse:
        """Render template with variables"""
        
        # Get template
        template = await self.get_template(template_id)
        
        if not template:
            raise ValueError(f"Template with ID {template_id} not found")
        
        if not template.is_active:
            raise ValueError(f"Template {template.name} is not active")
        
        # Validate variables
        if template.variables:
            is_valid, missing = self.render_service.validate_variables(
                template.variables,
                variables
            )
            
            if not is_valid:
                raise ValueError(f"Missing required variables: {', '.join(missing)}")
        
        # Render template
        rendered = await self.render_service.render(
            subject=template.subject,
            body_html=template.body_html,
            body_text=template.body_text,
            variables=variables
        )
        
        return RenderResponse(
            subject=rendered["subject"],
            body_html=rendered["body_html"],
            body_text=rendered["body_text"],
            template_id=template_id,
            variables_used=variables
        )