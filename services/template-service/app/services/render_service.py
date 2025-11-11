from jinja2 import Template, TemplateError, Environment, StrictUndefined
from typing import Dict, Any
import re


class RenderService:
    """Service for rendering templates with Jinja2"""
    
    def __init__(self):
        # Create Jinja2 environment with strict undefined (raises error on missing variables)
        self.env = Environment(
            autoescape=True,
            undefined=StrictUndefined,  # Raise error if variable is missing
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    async def render(
        self,
        subject: str,
        body_html: str,
        body_text: str,
        variables: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Render template with variables
        
        Args:
            subject: Subject template
            body_html: HTML body template
            body_text: Text body template
            variables: Variables to substitute
            
        Returns:
            Dict with rendered subject, body_html, body_text
            
        Raises:
            ValueError: If template rendering fails
        """
        try:
            # Render subject
            subject_template = self.env.from_string(subject)
            rendered_subject = subject_template.render(**variables)
            
            # Render HTML body
            html_template = self.env.from_string(body_html)
            rendered_html = html_template.render(**variables)
            
            # Render text body
            text_template = self.env.from_string(body_text)
            rendered_text = text_template.render(**variables)
            
            return {
                "subject": rendered_subject,
                "body_html": rendered_html,
                "body_text": rendered_text
            }
            
        except TemplateError as e:
            raise ValueError(f"Template rendering error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Unexpected error during rendering: {str(e)}")
    
    def extract_variables(self, template_string: str) -> list[str]:
        """
        Extract variable names from a template string
        
        Args:
            template_string: Template string with {{variable}} syntax
            
        Returns:
            List of unique variable names
        """
        # Match {{variable_name}} pattern
        pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
        matches = re.findall(pattern, template_string)
        
        # Return unique variables
        return list(set(matches))
    
    def validate_variables(
        self,
        required_variables: list[str],
        provided_variables: Dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """
        Validate that all required variables are provided
        
        Args:
            required_variables: List of required variable names
            provided_variables: Dict of provided variables
            
        Returns:
            Tuple of (is_valid, missing_variables)
        """
        provided_keys = set(provided_variables.keys())
        required_keys = set(required_variables)
        
        missing = required_keys - provided_keys
        
        return len(missing) == 0, list(missing)