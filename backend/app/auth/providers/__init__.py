"""Provider registry.

To add a provider (GitHub, Apple, ...): create providers/<name>.py with an IdentityProvider
subclass exposing `from_config(config)`, then add it to PROVIDER_FACTORIES below.
Nothing in services, routes or models changes.
"""
from flask import current_app

from app.auth.providers.base import IdentityProvider, VerifiedIdentity
from app.auth.providers.google import GoogleProvider
from app.errors import ApiError

PROVIDER_FACTORIES = {
    "google": GoogleProvider.from_config,
}


def init_providers(app) -> None:
    providers = {}
    for name, factory in PROVIDER_FACTORIES.items():
        provider = factory(app.config)
        if provider is not None:
            providers[name] = provider
    app.extensions["identity_providers"] = providers


def get_provider(name: str) -> IdentityProvider:
    provider = current_app.extensions["identity_providers"].get(name)
    if provider is None:
        raise ApiError(404, "unknown_provider", f"Sign-in provider '{name}' is not available.")
    return provider


def enabled_providers() -> list[str]:
    return sorted(current_app.extensions["identity_providers"])


__all__ = ["IdentityProvider", "VerifiedIdentity", "init_providers", "get_provider", "enabled_providers"]
