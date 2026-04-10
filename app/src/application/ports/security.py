"""Security-related ports for the application layer."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from domain import UserId


@dataclass(frozen=True, slots=True)
class TokenPair:
    """Token payload returned by authentication use cases."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@runtime_checkable
class PasswordHasher(Protocol):
    """Password hashing contract."""

    def hash(self, plain_password: str) -> str:
        """Hash a plain text password."""

    def verify(self, plain_password: str, password_hash: str) -> bool:
        """Verify that a plain text password matches a stored hash."""


@runtime_checkable
class JWTProvider(Protocol):
    """JWT creation and parsing contract."""

    def issue_tokens(self, *, subject: UserId) -> TokenPair:
        """Create access and refresh tokens for a subject."""

    def refresh_access_token(self, refresh_token: str) -> str:
        """Create a new access token from a refresh token."""

    def decode_subject(self, token: str) -> UserId:
        """Decode a token and return its subject identifier."""
