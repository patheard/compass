"""Base validation and service classes for extensibility across models."""

import re
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Type, TypeVar, Generic
from pydantic import BaseModel, ValidationError, validator
import html
from fastapi import HTTPException

# Generic type for model classes
ModelType = TypeVar("ModelType")


class BaseInputValidator(BaseModel):
    """Base validation class with common security protections."""

    @validator("*", pre=True)
    def sanitize_strings(cls, value: Any) -> Any:
        """Sanitize string inputs to prevent XSS and injection attacks."""
        if isinstance(value, str):
            # HTML escape to prevent XSS
            value = html.escape(value.strip())

            # Check for suspicious patterns
            suspicious_patterns = [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"on\w+\s*=",
                r"expression\s*\(",
                r"@import",
                r"url\s*\(",
                r"<!--.*?-->",
            ]

            for pattern in suspicious_patterns:
                if re.search(pattern, value, re.IGNORECASE | re.DOTALL):
                    raise ValueError("Input contains potentially malicious content")

        return value


class BaseService(Generic[ModelType], ABC):
    """Base service class for CRUD operations with security checks."""

    def __init__(self, model_class: Type[ModelType]):
        self.model_class = model_class

    @abstractmethod
    def validate_ownership(self, entity: ModelType, user_id: str) -> bool:
        """Validate that the user owns or has access to the entity."""
        pass

    @abstractmethod
    def get_user_entities(self, user_id: str) -> List[ModelType]:
        """Get all entities belonging to a user."""
        pass

    def validate_user_access(self, entity: ModelType, user_id: str) -> None:
        """Raise HTTPException if user doesn't have access to entity."""
        if not self.validate_ownership(entity, user_id):
            raise HTTPException(
                status_code=403, detail="Access denied: insufficient permissions"
            )

    def get_entity_or_404(self, entity_id: str, user_id: str) -> ModelType:
        """Get entity by ID and validate user access, or raise 404."""
        try:
            entity = self.model_class.get(entity_id)
            self.validate_user_access(entity, user_id)
            return entity
        except self.model_class.DoesNotExist:
            raise HTTPException(status_code=404, detail="Entity not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


class CSRFTokenManager:
    """CSRF token management for form protection."""

    @staticmethod
    def generate_csrf_token() -> str:
        """Generate a secure CSRF token."""
        import secrets

        return secrets.token_urlsafe(32)

    @staticmethod
    def validate_csrf_token(
        session_token: Optional[str], form_token: Optional[str]
    ) -> bool:
        """Validate CSRF token from form against session token."""
        if not session_token or not form_token:
            return False
        return session_token == form_token


def format_validation_error(error: Exception) -> str:
    """Convert pydantic ValidationError (and common ValueError) into a markdown format."""
    # If it's a pydantic ValidationError, try to build a compact, human-friendly message
    if isinstance(error, ValidationError):
        try:
            error_list = error.errors()
        except Exception:
            return str(error)

        parts: list[str] = []
        for e in error_list:
            # message may appear under different keys across versions
            msg = e.get("msg") or e.get("message") or e.get("error") or str(e)
            # Clean up repetitive phrasing like 'Value error, '
            if isinstance(msg, str) and msg.startswith("Value error, "):
                msg = msg[len("Value error, ") :]

            parts.append(f"- {msg}")

        return "\n".join(parts)

    return str(error)
