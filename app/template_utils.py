"""Template utilities for localized responses."""

from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import Any, Dict
from app.localization import (
    configure_jinja_i18n, 
    get_user_preferred_language
)


class LocalizedTemplates:
    """Template manager that automatically handles localization."""
    
    def __init__(self, directory: str):
        self.templates = Jinja2Templates(directory=directory)
    
    def TemplateResponse(
        self, 
        request: Request, 
        name: str, 
        context: Dict[str, Any]
    ) -> HTMLResponse:
        """Create a template response with automatic localization."""
        # Get user's preferred language
        accept_language = request.headers.get('accept-language', '')
        language = get_user_preferred_language(accept_language)
        
        # Configure Jinja2 environment with localization
        configure_jinja_i18n(self.templates.env, language)
        
        # The translation function is now available globally in templates as '_'
        return self.templates.TemplateResponse(name, context)