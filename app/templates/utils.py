"""Template utilities for localized responses."""

import os
from typing import Any, Dict

from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from markupsafe import Markup

import markdown as md
import bleach

from app.localization.utils import configure_jinja_i18n
from app.localization.middleware import get_request_locale


class LocalizedTemplates:
    """Template manager that automatically handles localization."""

    def __init__(self, directory: str):
        self.templates = Jinja2Templates(directory=directory)

        # Register a `markdown` filter on the Jinja2 environment
        self.templates.env.filters["markdown"] = self._markdown_to_html
        self.templates.env.filters["markdown_no_tags"] = self._markdown_no_tags

    def _markdown_no_tags(self, text: str) -> str:
        """Convert Markdown to plain text by stripping all HTML tags."""
        if not text:
            return ""

        # Convert markdown to HTML. Use a couple of safe extensions.
        html = md.markdown(text, extensions=["extra", "sane_lists"])

        # Strip all HTML tags to get plain text
        cleaned = bleach.clean(html, tags=[], strip=True)
        return Markup(cleaned)  # nosec: B704 Bandit flags use on untrusted input

    def _markdown_to_html(self, text: str) -> Markup:
        """Convert Markdown to sanitized HTML and mark it safe for Jinja2"""
        if not text:
            return Markup("")

        # Convert markdown to HTML. Use a couple of safe extensions.
        html = md.markdown(text, extensions=["extra", "sane_lists"])

        # Allowed tags and attributes: start from bleach defaults and extend
        allowed_tags = set(bleach.sanitizer.ALLOWED_TAGS) | {
            "a",
            "br",
            "code",
            "h1",
            "h2",
            "h3",
            "h4",
            "hr",
            "img",
            "li",
            "ol",
            "p",
            "pre",
            "span",
            "ul",
        }
        allowed_attrs = {
            **bleach.sanitizer.ALLOWED_ATTRIBUTES,
            "a": ["href", "title", "rel", "target"],
            "code": ["class"],
            "img": ["src", "alt", "title"],
            "span": ["class"],
        }

        cleaned = bleach.clean(
            html,
            tags=list(allowed_tags),
            attributes=allowed_attrs,
            strip=True,
        )

        # Convert URLs into clickable links (keeps them sanitized)
        linked = bleach.linkify(cleaned)
        return Markup(linked)  # nosec: B704 Bandit flags use on untrusted input

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
