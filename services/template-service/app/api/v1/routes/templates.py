from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from typing import Optional

from app.schemas.template import (
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
    TemplateList
)
from app.schemas.common import APIResponse, PaginationMeta
from app.services.template_service import TemplateService
from app.api.dependencies import get_template_service

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.post("/", response_model=APIResponse[TemplateResponse], status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: TemplateCreate,
    service: TemplateService = Depends(get_template_service)
):
    """
    Create a new notification template
    
    - **name**: Unique template name
    - **subject**: Email subject line (supports Jinja2 variables)
    - **body_html**: HTML email body (supports Jinja2 variables)
    - **body_text**: Plain text email body (supports Jinja2 variables)
    - **variables**: List of required variables (auto-extracted if not provided)
    - **template_type**: Type of template (email, push, sms)
    - **language**: Language code (ISO 639-1, default: en)
    """
    try:
        template = await service.create_template(template_data)
        return APIResponse(
            success=True,
            data=template,
            message="Template created successfully",
            meta=None
        )
    except ValueError as e:  
        raise HTTPException(  
            status_code=status.HTTP_409_CONFLICT,  # ✅ Correct for duplicates  
            detail=str(e)  
    )  
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create template: {str(e)}"
        )


@router.get("/{template_id}", response_model=APIResponse[TemplateResponse])
async def get_template(
    template_id: UUID,
    service: TemplateService = Depends(get_template_service)
):
    """
    Get template by ID
    
    Returns template details including all fields and metadata.
    Results are cached for better performance.
    """
    template = await service.get_template(template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with ID {template_id} not found"
        )
    
    return APIResponse(
        success=True,
        data=template,
        message="Template retrieved successfully",
        meta=None
    )


@router.get("/name/{template_name}", response_model=APIResponse[TemplateResponse])
async def get_template_by_name(
    template_name: str,
    service: TemplateService = Depends(get_template_service)
):
    """
    Get template by name
    
    Alternative way to fetch templates using their unique name.
    Results are cached for better performance.
    """
    template = await service.get_template_by_name(template_name)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with name '{template_name}' not found"
        )
    
    return APIResponse(
        success=True,
        data=template,
        message="Template retrieved successfully",
        meta=None
    )


@router.get("/", response_model=APIResponse[TemplateList])
async def list_templates(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    template_type: Optional[str] = Query(None, description="Filter by template type"),
    language: Optional[str] = Query(None, description="Filter by language"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    service: TemplateService = Depends(get_template_service)
):
    """
    List all templates with pagination and filters
    
    - **page**: Page number (starts from 1)
    - **limit**: Number of items per page (max 100)
    - **template_type**: Filter by type (email, push, sms)
    - **language**: Filter by language code (e.g., en, es)
    - **is_active**: Filter by active status (true/false)
    """
    skip = (page - 1) * limit
    
    templates, total = await service.get_templates(
        skip=skip,
        limit=limit,
        template_type=template_type,
        language=language,
        is_active=is_active
    )
    
    total_pages = (total + limit - 1) // limit
    
    template_list = TemplateList(
        templates=templates,
        total=total,
        page=page,
        limit=limit
    )
    
    pagination_meta = PaginationMeta(
        total=total,
        limit=limit,
        page=page,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )
    
    return APIResponse(
        success=True,
        data=template_list,
        message=f"Retrieved {len(templates)} templates",
        meta=pagination_meta
    )


@router.put("/{template_id}", response_model=APIResponse[TemplateResponse])
async def update_template(
    template_id: UUID,
    template_data: TemplateUpdate,
    service: TemplateService = Depends(get_template_service)
):
    """
    Update template
    
    All fields are optional. Only provided fields will be updated.
    Version number is automatically incremented when content changes.
    """
    try:
        template = await service.update_template(template_id, template_data)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template with ID {template_id} not found"
            )
        
        return APIResponse(
            success=True,
            data=template,
            message="Template updated successfully",
            meta=None
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{template_id}", response_model=APIResponse)
async def delete_template(
    template_id: UUID,
    service: TemplateService = Depends(get_template_service)
):
    """
    Delete template (soft delete)
    
    Sets is_active to False instead of permanently deleting.
    Deleted templates can be reactivated by updating is_active field.
    """
    success = await service.delete_template(template_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with ID {template_id} not found"
        )
    
    return APIResponse(
        success=True,
        data={"template_id": str(template_id), "deleted": True},
        message="Template deleted successfully",
        meta=None
    )