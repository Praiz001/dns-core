from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from uuid import UUID

from app.models.template import Template
from app.schemas.template import TemplateCreate, TemplateUpdate


class TemplateRepository:
    """Repository for template database operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, template_data: TemplateCreate) -> Template:
        """Create a new template"""
        try:
            template = Template(
                name=template_data.name,
                description=template_data.description,
                subject=template_data.subject,
                body_html=template_data.body_html,
                body_text=template_data.body_text,
                variables=template_data.variables,
                template_type=template_data.template_type,
                language=template_data.language,
            )
            
            self.db.add(template)
            await self.db.commit()
            await self.db.refresh(template)
            
            return template
            
        except IntegrityError:
            await self.db.rollback()
            raise ValueError(f"Template with name '{template_data.name}' already exists")
    
    async def get_by_id(self, template_id: UUID) -> Optional[Template]:
        """Get template by ID"""
        result = await self.db.execute(
            select(Template).where(Template.id == template_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str) -> Optional[Template]:
        """Get template by name"""
        result = await self.db.execute(
            select(Template).where(Template.name == name)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 10,
        template_type: Optional[str] = None,
        language: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> tuple[List[Template], int]:
        """Get all templates with pagination and filters"""
        
        # Build query
        query = select(Template)
        
        # Apply filters
        if template_type:
            query = query.where(Template.template_type == template_type)
        if language:
            query = query.where(Template.language == language)
        if is_active is not None:
            query = query.where(Template.is_active == is_active)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.offset(skip).limit(limit).order_by(Template.created_at.desc())
        
        # Execute query
        result = await self.db.execute(query)
        templates = result.scalars().all()
        
        return list(templates), total
    
    async def update(self, template_id: UUID, template_data: TemplateUpdate) -> Optional[Template]:
        """Update template"""
        template = await self.get_by_id(template_id)
        
        if not template:
            return None
        
        # Update fields
        update_data = template_data.model_dump(exclude_unset=True)
        
        if update_data:
            # Increment version if content changes
            content_fields = ['subject', 'body_html', 'body_text']
            if any(field in update_data for field in content_fields):
                update_data['version'] = template.version + 1
            
            for field, value in update_data.items():
                setattr(template, field, value)
            
            await self.db.commit()
            await self.db.refresh(template)
        
        return template
    
    async def delete(self, template_id: UUID) -> bool:
        """Delete template (hard delete)"""
        template = await self.get_by_id(template_id)
        
        if not template:
            return False
        
        await self.db.delete(template)
        await self.db.commit()
        
        return True
    
    async def soft_delete(self, template_id: UUID) -> Optional[Template]:
        """Soft delete template (set is_active to False)"""
        template = await self.get_by_id(template_id)
        
        if not template:
            return None
        
        template.is_active = False
        await self.db.commit()
        await self.db.refresh(template)
        
        return template