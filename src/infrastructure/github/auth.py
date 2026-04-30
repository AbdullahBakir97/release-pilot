"""GitHub App JWT authentication and installation token management."""

from __future__ import annotations

import time

import httpx
import jwt  # PyJWT

__all__ = ["GitHubAuthenticator"]


class GitHubAuthenticator:
    """Handles GitHub App JWT generation and installation access tokens.

    Generates short-lived JWTs signed with the App's private key (RS256)
    and exchanges them for installation access tokens, caching results
    with an expiry buffer to minimise round-trips.
    """

    def __init__(self, app_id: str, private_key: str) -> None:
        self._app_id = app_id
        self._private_key = private_key
        self._token_cache: dict[int, tuple[str, float]] = {}

    def generate_jwt(self) -> str:
        """Create a short-lived JWT for authenticating as the GitHub App."""
        now = int(time.time())
        payload = {"iat": now - 60, "exp": now + 600, "iss": self._app_id}
        return jwt.encode(payload, self._private_key, algorithm="RS256")

    async def get_installation_token(self, installation_id: int) -> str:
        """Obtain an installation access token, using the cache when possible.

        Args:
            installation_id: The GitHub App installation ID.

        Returns:
            A valid installation access token string.
        """
        if installation_id in self._token_cache:
            token, expires_at = self._token_cache[installation_id]
            if time.time() < expires_at - 60:
                return token

        jwt_token = self.generate_jwt()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        token = data["token"]
        self._token_cache[installation_id] = (token, time.time() + 3300)
        return token
