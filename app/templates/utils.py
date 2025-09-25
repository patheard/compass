"""Template utilities for localized responses."""

import os
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import Any, Dict
from app.localization.utils import configure_jinja_i18n
from app.localization.middleware import get_request_locale


class LocalizedTemplates:
    """Template manager that automatically handles localization."""

    def __init__(self, directory: str):
        self.templates = Jinja2Templates(directory=directory)

    def TemplateResponse(
        self,
        request: Request,
        name: str,
        context: Dict[str, Any],
        status_code: int = 200,
    ) -> HTMLResponse:
        """Create a template response with automatic localization."""
        # Get user's preferred language from request state (set by middleware)
        language = get_request_locale(request)

        # Configure Jinja2 environment with localization
        configure_jinja_i18n(self.templates.env, language)

        # Add version from environment variable
        context["version"] = os.getenv("APP_VERSION", "1.0.0")

        # The translation function is now available globally in templates as '_'
        return self.templates.TemplateResponse(name, context, status_code=status_code)
