"""Base model for PynamoDB with common functionality."""

from datetime import datetime, timezone
from typing import Any, Dict, Type, TypeVar

from pynamodb.attributes import UTCDateTimeAttribute
from pynamodb.models import Model

from app.database.config import db_config

T = TypeVar("T", bound="BaseModel")


class BaseModel(Model):
    """Base model with common functionality for all DynamoDB models."""

    class Meta:
        """Meta configuration for PynamoDB."""

        region = db_config.region
        if db_config.endpoint_url:
            host = db_config.endpoint_url

    created_at: UTCDateTimeAttribute = UTCDateTimeAttribute(
        default=datetime.now(timezone.utc)
    )
    updated_at: UTCDateTimeAttribute = UTCDateTimeAttribute(
        default=datetime.now(timezone.utc)
    )

    def save(self, **kwargs: Any) -> Dict[str, Any]:
        """Save the model with updated timestamp."""
        self.updated_at = datetime.now(timezone.utc)
        return super().save(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        result = {}
        for attr_name in self.get_attributes():
            attr = getattr(self.__class__, attr_name)
            value = getattr(self, attr_name)
            if value is not None:
                if hasattr(attr, "serialize"):
                    result[attr_name] = attr.serialize(value)
                else:
                    result[attr_name] = value
        return result

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create model instance from dictionary."""
        kwargs = {}
        for attr_name in cls.get_attributes():
            if attr_name in data:
                kwargs[attr_name] = data[attr_name]
        return cls(**kwargs)

    @classmethod
    def get_table_name(cls) -> str:
        """Get the table name for this model."""
        return cls.Meta.table_name

    @classmethod
    def create_table_if_not_exists(
        cls, read_capacity_units: int = 5, write_capacity_units: int = 5
    ) -> bool:
        """Create the table if it doesn't exist."""
        if not cls.exists():
            cls.create_table(
                read_capacity_units=read_capacity_units,
                write_capacity_units=write_capacity_units,
                wait=True,
            )
            return True
        return False
