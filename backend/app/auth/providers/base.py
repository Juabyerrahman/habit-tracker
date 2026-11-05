from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class VerifiedIdentity:
    """What every provider must return after verifying a credential."""

    provider: str
    subject: str  # provider's stable user id
    email: str
    email_verified: bool
    name: str = ""


class IdentityProvider(ABC):
    name: str

    @abstractmethod
    def verify(self, credential: str) -> VerifiedIdentity:
        """Validate the credential with the provider. Raise ApiError if invalid."""
