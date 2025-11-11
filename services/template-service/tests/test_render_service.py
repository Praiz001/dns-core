import pytest
from app.services.render_service import RenderService


class TestRenderService:
    """Test cases for RenderService"""
    
    @pytest.fixture
    def render_service(self):
        return RenderService()
    
    @pytest.mark.asyncio
    async def test_render_simple_template(self, render_service):
        """Test rendering a simple template"""
        subject = "Hello {{name}}"
        body_html = "<h1>Welcome {{name}}!</h1>"
        body_text = "Welcome {{name}}!"
        variables = {"name": "John"}
        
        result = await render_service.render(subject, body_html, body_text, variables)
        
        assert result["subject"] == "Hello John"
        assert result["body_html"] == "<h1>Welcome John!</h1>"
        assert result["body_text"] == "Welcome John!"
    
    @pytest.mark.asyncio
    async def test_render_multiple_variables(self, render_service):
        """Test rendering with multiple variables"""
        subject = "Order #{{order_id}} Confirmation"
        body_html = "<p>Hi {{user_name}}, your order #{{order_id}} for {{amount}} is confirmed.</p>"
        body_text = "Hi {{user_name}}, your order #{{order_id}} for {{amount}} is confirmed."
        variables = {
            "user_name": "John Doe",
            "order_id": "ORD-12345",
            "amount": "$99.99"
        }
        
        result = await render_service.render(subject, body_html, body_text, variables)
        
        assert "Order #ORD-12345 Confirmation" in result["subject"]
        assert "John Doe" in result["body_html"]
        assert "ORD-12345" in result["body_html"]
        assert "$99.99" in result["body_text"]
    
    @pytest.mark.asyncio
    async def test_render_missing_variable_raises_error(self, render_service):
        """Test that missing variables raise an error"""
        subject = "Hello {{name}}"
        body_html = "<h1>Welcome {{name}}!</h1>"
        body_text = "Welcome {{name}}!"
        variables = {}  # Missing 'name'
        
        with pytest.raises(ValueError):
            await render_service.render(subject, body_html, body_text, variables)
    
    def test_extract_variables(self, render_service):
        """Test extracting variables from template string"""
        template = "Hello {{name}}, your order {{order_id}} is ready. Contact {{support_email}}."
        
        variables = render_service.extract_variables(template)
        
        assert "name" in variables
        assert "order_id" in variables
        assert "support_email" in variables
        assert len(variables) == 3
    
    def test_extract_variables_with_duplicates(self, render_service):
        """Test extracting variables with duplicates"""
        template = "{{name}} {{name}} {{email}} {{name}}"
        
        variables = render_service.extract_variables(template)
        
        # Should return unique variables only
        assert len(variables) == 2
        assert "name" in variables
        assert "email" in variables
    
    def test_validate_variables_success(self, render_service):
        """Test successful variable validation"""
        required = ["name", "email"]
        provided = {"name": "John", "email": "john@example.com", "extra": "value"}
        
        is_valid, missing = render_service.validate_variables(required, provided)
        
        assert is_valid is True
        assert len(missing) == 0
    
    def test_validate_variables_missing(self, render_service):
        """Test validation with missing variables"""
        required = ["name", "email", "phone"]
        provided = {"name": "John"}
        
        is_valid, missing = render_service.validate_variables(required, provided)
        
        assert is_valid is False
        assert "email" in missing
        assert "phone" in missing
        assert len(missing) == 2