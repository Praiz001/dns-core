from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.template import RenderRequest, RenderResponse
from app.schemas.common import APIResponse
from app.services.template_service import TemplateService
from app.api.dependencies import get_template_service

router = APIRouter(prefix="/templates", tags=["Template Rendering"])


@router.post("/render", response_model=APIResponse[RenderResponse])
async def render_template(
    render_request: RenderRequest,
    service: TemplateService = Depends(get_template_service)
):
    """
    Render template with variables
    
    Takes a template ID and a dictionary of variables, then returns
    the rendered subject, HTML body, and text body.
    
    **Example Request:**
    ```json
    {
        "template_id": "550e8400-e29b-41d4-a716-446655440000",
        "variables": {
            "user_name": "John Doe",
            "order_id": "ORD-12345",
            "amount": "$99.99"
        }
    }
    ```
    
    **Example Response:**
    ```json
    {
        "success": true,
        "data": {
            "subject": "Order Confirmation #ORD-12345",
            "body_html": "<h1>Hi John Doe!</h1><p>Your order...</p>",
            "body_text": "Hi John Doe! Your order...",
            "template_id": "550e8400-e29b-41d4-a716-446655440000",
            "variables_used": {
                "user_name": "John Doe",
                "order_id": "ORD-12345",
                "amount": "$99.99"
            }
        },
        "message": "Template rendered successfully"
    }
    ```
    
    **Validation:**
    - Template must exist and be active
    - All required variables must be provided
    - Variables are validated against template's variable list
    
    **Errors:**
    - 404: Template not found
    - 400: Missing required variables or rendering error
    """
    try:
        rendered = await service.render_template(
            template_id=render_request.template_id,
            variables=render_request.variables
        )
        
        return APIResponse(
            success=True,
            data=rendered,
            message="Template rendered successfully",
            meta=None
        )
        
    except ValueError as e:
        # Handle validation errors (missing variables, inactive template, etc.)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to render template: {str(e)}"
        )