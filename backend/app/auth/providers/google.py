
import hmac

from flask import current_app
from google.auth.exceptions import TransportError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.auth.providers.base import IdentityProvider, VerifiedIdentity
from app.errors import ApiError


class GoogleProvider(IdentityProvider):
    """Verifies Google ID tokens (signature, expiry, issuer, audience)."""

    name = "google"

    def __init__(self, client_id: str):
        self._client_id = client_id
        self._http = google_requests.Request()

    @classmethod
    def from_config(cls, config):
        client_id = config.get("GOOGLE_CLIENT_ID")
        return cls(client_id) if client_id else None

    def verify(
        self,
        credential: str,
        *,
        nonce: str | None = None
    ) -> VerifiedIdentity:

        # Step 1: Verify Google's ID token.
        try:
            claims = id_token.verify_oauth2_token(
                credential,
                self._http,
                self._client_id
            )

        except TransportError:
            current_app.logger.warning(
                "Google token verification failed: Google unavailable."
            )
            raise ApiError(
                503,
                "provider_unavailable",
                "Google could not be reached. Try again shortly."
            ) from None

        except ValueError as exc:
            current_app.logger.warning(
                "Google ID token verification failed: %s: %s",
                type(exc).__name__,
                str(exc)[:200]
            )
            raise ApiError(
                401,
                "invalid_credential",
                "Google sign-in could not be verified."
            ) from None

        # Step 2: Verify OAuth nonce.
        if nonce is not None:
            token_nonce = str(claims.get("nonce", ""))

            if not hmac.compare_digest(token_nonce, nonce):
                current_app.logger.warning(
                    "Google ID token nonce mismatch."
                )
                raise ApiError(
                    401,
                    "invalid_credential",
                    "Google sign-in could not be verified."
                )

        # Step 3: Validate email.
        email = (claims.get("email") or "").lower()

        if not email or not claims.get("email_verified"):
            current_app.logger.warning(
                "Google account has no verified email."
            )
            raise ApiError(
                403,
                "email_not_verified",
                "Your Google account email is not verified."
            )

        # Step 4: Return verified identity.
        return VerifiedIdentity(
            "google",
            claims["sub"],
            email,
            True,
            (claims.get("name") or "")[:100]
      )