from datetime import datetime, timezone
from secrets import token_urlsafe
from sqlalchemy import Boolean, Integer, String, Text, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from flaskr import db
import hmac
import hashlib


class Interaction(db.Model):
    __tablename__ = 'x_interactions'  # Define table name

    interaction_id: Mapped[str] = mapped_column(String(64), primary_key=True)  # Primary Key
    media_account: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # Media account
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # User ID
    username: Mapped[str] = mapped_column(String(255), nullable=False)  # Username
    avatar_url: Mapped[str] = mapped_column(String(255), nullable=True)  # Avatar URL
    interaction_type: Mapped[str] = mapped_column(String(20), nullable=False)  # Interaction type
    interaction_content: Mapped[str] = mapped_column(Text,
                                                     nullable=True)  # Interaction content (optional, for comments)
    interaction_time: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)  # Interaction time
    post_id: Mapped[str] = mapped_column(String(64), nullable=True)  # Post ID, for association
    post_time: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=True)  # Post publish time
    nostr_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)  # Whether published to nostr
    nostr_event_id: Mapped[str] = mapped_column(String(64), nullable=True)  # nostr event ID
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False,
                                                 default=lambda: datetime.now(timezone.utc))  # sync timestamp


class ApiKey(db.Model):
    __tablename__ = 'x_api_keys'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    api_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    api_secret: Mapped[str] = mapped_column(String(64), nullable=False)  # 新增：API Secret
    api_name: Mapped[str] = mapped_column(String(128), nullable=False)  # Key owner or purpose
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=True)
    last_used_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=True)

    @staticmethod
    def generate_credentials() -> tuple[str, str]:
        # generate api key and secret
        return token_urlsafe(32), token_urlsafe(32)

    def is_valid(self) -> bool:
        """Check if the API key is valid"""
        now = datetime.now(timezone.utc)
        return (
                self.is_active and
                (self.expires_at is None or self.expires_at > now)
        )

    def verify_hmac(self, signature: str, message: str) -> bool:
        """Verify HMAC signature"""
        expected = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)
