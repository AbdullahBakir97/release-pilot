"""GitHub infrastructure -- API client, auth, webhook verification."""

from .auth import GitHubAuthenticator
from .client import GitHubClient
from .webhook import WebhookVerifier

__all__ = ["GitHubAuthenticator", "GitHubClient", "WebhookVerifier"]
