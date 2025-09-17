"""Users table model for PynamoDB."""

from datetime import datetime, timezone
from typing import Optional

from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection

from app.database.base import BaseModel
from app.database.config import db_config


class EmailIndex(GlobalSecondaryIndex):
    """Global secondary index for email lookups."""

    class Meta:
        """Meta configuration for the email index."""

        index_name = "email-index"
        projection = AllProjection()
        read_capacity_units = 5
        write_capacity_units = 5

    email = UnicodeAttribute(hash_key=True)


class User(BaseModel):
    """User model for storing authentication and profile data."""

    class Meta:
        """Meta configuration for the Users table."""

        table_name = db_config.users_table_name
        region = db_config.region
        if db_config.endpoint_url:
            host = db_config.endpoint_url

    # Primary key
    user_id = UnicodeAttribute(hash_key=True)  # Google sub ID

    # User attributes
    email = UnicodeAttribute()
    name = UnicodeAttribute()
    google_id = UnicodeAttribute()  # Same as user_id
    last_login = UTCDateTimeAttribute(null=True)

    # Global secondary index
    email_index = EmailIndex()

    def __init__(
        self,
        user_id: str,
        email: str,
        name: str,
        google_id: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Initialize User model."""
        super().__init__(
            user_id=user_id,
            email=email,
            name=name,
            google_id=google_id or user_id,
            **kwargs,
        )

    def update_last_login(self) -> None:
        """Update the last login timestamp."""
        self.last_login = datetime.now(timezone.utc)
        self.save()

    @classmethod
    def get_by_email(cls, email: str) -> Optional["User"]:
        """Get user by email address."""
        try:
            return next(iter(cls.email_index.query(email)))
        except StopIteration:
            return None

    @classmethod
    def get_by_google_id(cls, google_id: str) -> Optional["User"]:
        """Get user by Google ID (same as user_id)."""
        try:
            return cls.get(google_id)
        except cls.DoesNotExist:
            return None

    @classmethod
    def create_user(cls, google_id: str, email: str, name: str) -> "User":
        """Create a new user."""
        user = cls(user_id=google_id, email=email, name=name, google_id=google_id)
        user.save()
        return user
