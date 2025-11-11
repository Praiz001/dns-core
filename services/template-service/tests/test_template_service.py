import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from app.services.template_service import TemplateService
from app.services.render_service import RenderService
from app.db.repositories.template_repository import TemplateRepository
from app.schemas.template import TemplateCreate, TemplateUpdate, TemplateResponse
from app.models.template import Template
from datetime import datetime


@pytest.fixture
def mock_repository():
    """Mock template repository"""
    return AsyncMock(spec=TemplateRepository)


@pytest.fixture
def mock_render_service():
    """Mock render service"""
    service = MagicMock(spec=RenderService)
    service.extract_variables = MagicMock(return_value=["name", "email"])
    service.validate_variables = MagicMock(return_value=(True, []))
    return service


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    redis.delete_pattern = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def template_service(mock_repository, mock_render_service, mock_redis):
    """Create template service with mocked dependencies"""
    return TemplateService(mock_repository, mock_render_service, mock_redis)


@pytest.fixture
def sample_template():
    """Sample template model"""
    return Template(
        id=uuid4(),
        name="test_template",
        description="Test template",
        subject="Hello {{name}}",
        body_html="<h1>Hello {{name}}!</h1>",
        body_text="Hello {{name}}!",
        variables=["name"],
        template_type="email",
        language="en",
        version=1,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestTemplateService:
    """Test cases for TemplateService"""
    
    @pytest.mark.asyncio
    async def test_create_template(self, template_service, mock_repository, sample_template):
        """Test creating a new template"""
        template_data = TemplateCreate(
            name="test_template",
            subject="Hello {{name}}",
            body_html="<h1>Hello {{name}}!</h1>",
            body_text="Hello {{name}}!",
            template_type="email",
            language="en"
        )
        
        mock_repository.create.return_value = sample_template
        
        result = await template_service.create_template(template_data)
        
        assert isinstance(result, TemplateResponse)
        assert result.name == "test_template"
        assert result.template_type == "email"
        mock_repository.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_template_auto_extract_variables(
        self, 
        template_service, 
        mock_repository, 
        mock_render_service,
        sample_template
    ):
        """Test template creation with auto-extracted variables"""
        template_data = TemplateCreate(
            name="test_template",
            subject="Hello {{name}}",
            body_html="<h1>Hello {{name}} and {{email}}!</h1>",
            body_text="Hello {{name}}!",
            template_type="email",
            language="en"
        )
        
        mock_repository.create.return_value = sample_template
        
        result = await template_service.create_template(template_data)
        
        # Verify variables were auto-extracted
        mock_render_service.extract_variables.assert_called()
        assert result.name == "test_template"
    
    @pytest.mark.asyncio
    async def test_get_template_by_id(self, template_service, mock_repository, sample_template):
        """Test getting template by ID"""
        template_id = sample_template.id
        mock_repository.get_by_id.return_value = sample_template
        
        result = await template_service.get_template(template_id)
        
        assert result is not None
        assert result.id == template_id
        assert result.name == "test_template"
        mock_repository.get_by_id.assert_called_once_with(template_id)
    
    @pytest.mark.asyncio
    async def test_get_template_not_found(self, template_service, mock_repository):
        """Test getting non-existent template"""
        template_id = uuid4()
        mock_repository.get_by_id.return_value = None
        
        result = await template_service.get_template(template_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_template_by_name(self, template_service, mock_repository, sample_template):
        """Test getting template by name"""
        mock_repository.get_by_name.return_value = sample_template
        
        result = await template_service.get_template_by_name("test_template")
        
        assert result is not None
        assert result.name == "test_template"
        mock_repository.get_by_name.assert_called_once_with("test_template")
    
    @pytest.mark.asyncio
    async def test_get_templates_with_pagination(self, template_service, mock_repository, sample_template):
        """Test getting templates with pagination"""
        templates = [sample_template]
        total = 1
        mock_repository.get_all.return_value = (templates, total)
        
        result, count = await template_service.get_templates(skip=0, limit=10)
        
        assert len(result) == 1
        assert count == 1
        assert result[0].name == "test_template"
        mock_repository.get_all.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_templates_with_filters(self, template_service, mock_repository, sample_template):
        """Test getting templates with filters"""
        templates = [sample_template]
        total = 1
        mock_repository.get_all.return_value = (templates, total)
        
        result, count = await template_service.get_templates(
            skip=0,
            limit=10,
            template_type="email",
            language="en",
            is_active=True
        )
        
        assert len(result) == 1
        mock_repository.get_all.assert_called_once_with(
            skip=0,
            limit=10,
            template_type="email",
            language="en",
            is_active=True
        )
    
    @pytest.mark.asyncio
    async def test_update_template(self, template_service, mock_repository, sample_template):
        """Test updating a template"""
        template_id = sample_template.id
        update_data = TemplateUpdate(
            subject="Updated subject",
            is_active=False
        )
        
        updated_template = sample_template
        updated_template.subject = "Updated subject"
        updated_template.is_active = False
        updated_template.version = 2
        
        mock_repository.update.return_value = updated_template
        
        result = await template_service.update_template(template_id, update_data)
        
        assert result is not None
        assert result.subject == "Updated subject"
        assert result.is_active is False
        mock_repository.update.assert_called_once_with(template_id, update_data)
    
    @pytest.mark.asyncio
    async def test_update_template_not_found(self, template_service, mock_repository):
        """Test updating non-existent template"""
        template_id = uuid4()
        update_data = TemplateUpdate(subject="Updated")
        mock_repository.update.return_value = None
        
        result = await template_service.update_template(template_id, update_data)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_template(self, template_service, mock_repository, sample_template):
        """Test deleting a template (soft delete)"""
        template_id = sample_template.id
        deleted_template = sample_template
        deleted_template.is_active = False
        
        mock_repository.soft_delete.return_value = deleted_template
        
        result = await template_service.delete_template(template_id)
        
        assert result is True
        mock_repository.soft_delete.assert_called_once_with(template_id)
    
    @pytest.mark.asyncio
    async def test_delete_template_not_found(self, template_service, mock_repository):
        """Test deleting non-existent template"""
        template_id = uuid4()
        mock_repository.soft_delete.return_value = None
        
        result = await template_service.delete_template(template_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_render_template_success(
        self, 
        template_service, 
        mock_repository,
        mock_render_service,
        sample_template
    ):
        """Test rendering a template successfully"""
        template_id = sample_template.id
        variables = {"name": "John Doe"}
        
        # Mock getting template
        mock_repository.get_by_id.return_value = sample_template
        
        # Mock rendering
        mock_render_service.render = AsyncMock(return_value={
            "subject": "Hello John Doe",
            "body_html": "<h1>Hello John Doe!</h1>",
            "body_text": "Hello John Doe!"
        })
        
        # Set template service's get_template to return the template response
        template_service.get_template = AsyncMock(return_value=TemplateResponse(
            id=sample_template.id,
            name=sample_template.name,
            description=sample_template.description,
            subject=sample_template.subject,
            body_html=sample_template.body_html,
            body_text=sample_template.body_text,
            variables=sample_template.variables,
            template_type=sample_template.template_type,
            language=sample_template.language,
            version=sample_template.version,
            is_active=sample_template.is_active,
            created_at=sample_template.created_at,
            updated_at=sample_template.updated_at
        ))
        
        result = await template_service.render_template(template_id, variables)
        
        assert result.subject == "Hello John Doe"
        assert result.body_html == "<h1>Hello John Doe!</h1>"
        assert result.template_id == template_id
        assert result.variables_used == variables
    
    @pytest.mark.asyncio
    async def test_render_template_not_found(self, template_service, mock_repository):
        """Test rendering non-existent template"""
        template_id = uuid4()
        variables = {"name": "John"}
        
        template_service.get_template = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError, match="not found"):
            await template_service.render_template(template_id, variables)
    
    @pytest.mark.asyncio
    async def test_render_template_inactive(self, template_service, mock_repository, sample_template):
        """Test rendering inactive template"""
        template_id = sample_template.id
        variables = {"name": "John"}
        
        inactive_template = TemplateResponse(
            id=sample_template.id,
            name=sample_template.name,
            description=sample_template.description,
            subject=sample_template.subject,
            body_html=sample_template.body_html,
            body_text=sample_template.body_text,
            variables=sample_template.variables,
            template_type=sample_template.template_type,
            language=sample_template.language,
            version=sample_template.version,
            is_active=False,  # Inactive
            created_at=sample_template.created_at,
            updated_at=sample_template.updated_at
        )
        
        template_service.get_template = AsyncMock(return_value=inactive_template)
        
        with pytest.raises(ValueError, match="not active"):
            await template_service.render_template(template_id, variables)
    
    @pytest.mark.asyncio
    async def test_render_template_missing_variables(
        self, 
        template_service, 
        mock_repository,
        mock_render_service,
        sample_template
    ):
        """Test rendering template with missing variables"""
        template_id = sample_template.id
        variables = {}  # Missing 'name'
        
        # Mock validate_variables to return missing variables
        mock_render_service.validate_variables = MagicMock(return_value=(False, ["name"]))
        
        template_service.get_template = AsyncMock(return_value=TemplateResponse(
            id=sample_template.id,
            name=sample_template.name,
            description=sample_template.description,
            subject=sample_template.subject,
            body_html=sample_template.body_html,
            body_text=sample_template.body_text,
            variables=["name"],  # Required variable
            template_type=sample_template.template_type,
            language=sample_template.language,
            version=sample_template.version,
            is_active=sample_template.is_active,
            created_at=sample_template.created_at,
            updated_at=sample_template.updated_at
        ))
        
        with pytest.raises(ValueError, match="Missing required variables"):
            await template_service.render_template(template_id, variables)
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_create(
        self, 
        template_service, 
        mock_repository,
        mock_redis,
        sample_template
    ):
        """Test cache invalidation when creating template"""
        template_data = TemplateCreate(
            name="test_template",
            subject="Hello {{name}}",
            body_html="<h1>Hello {{name}}!</h1>",
            body_text="Hello {{name}}!",
            template_type="email",
            language="en"
        )
        
        mock_repository.create.return_value = sample_template
        
        await template_service.create_template(template_data)
        
        # Verify cache was invalidated
        mock_redis.delete_pattern.assert_called_with("templates:list:*")
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_update(
        self, 
        template_service, 
        mock_repository,
        mock_redis,
        sample_template
    ):
        """Test cache invalidation when updating template"""
        template_id = sample_template.id
        update_data = TemplateUpdate(subject="Updated")
        
        mock_repository.update.return_value = sample_template
        
        await template_service.update_template(template_id, update_data)
        
        # Verify cache was invalidated
        mock_redis.delete.assert_any_call(f"templates:id:{template_id}")
        mock_redis.delete.assert_any_call(f"templates:name:{sample_template.name}")
        mock_redis.delete_pattern.assert_called_with("templates:list:*")