"""
ServiceTitan authentication service.
"""

import time
from typing import Optional

import httpx
import structlog

from src.domain.exceptions.provider_error import ProviderAPIError

logger = structlog.get_logger()


class ServiceTitanAuth:
    """ServiceTitan OAuth2 authentication."""

    def __init__(self, client_id: str, client_secret: str, tenant_id: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[int] = None

        # ServiceTitan OAuth endpoints
        self.auth_url = f"https://auth.servicetitan.com/connect/token"

    async def get_access_token(self) -> str:
        """Get valid access token, refreshing if necessary."""
        if self._is_token_valid():
            return self.access_token

        await self._refresh_token()
        return self.access_token

    def _is_token_valid(self) -> bool:
        """Check if current token is still valid."""
        if not self.access_token or not self.token_expires_at:
            return False

        # Add 5 minute buffer before expiration
        buffer_time = 300
        return time.time() < (self.token_expires_at - buffer_time)

    async def _refresh_token(self) -> None:
        """Refresh access token."""
        try:
            auth_data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": f"servicetitan:{self.tenant_id}",
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.auth_url,
                    data=auth_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    raise ProviderAPIError(
                        "servicetitan",
                        response.status_code,
                        f"Authentication failed: {response.text}",
                    )

                token_data = response.json()
                self.access_token = token_data["access_token"]
                self.token_expires_at = time.time() + token_data["expires_in"]

                logger.info(
                    "ServiceTitan access token refreshed",
                    expires_in=token_data["expires_in"],
                )

        except httpx.TimeoutException:
            raise ProviderAPIError(
                "servicetitan", 408, "Authentication request timeout"
            )
        except httpx.RequestError as e:
            raise ProviderAPIError(
                "servicetitan", 0, f"Authentication network error: {str(e)}"
            )
        except Exception as e:
            logger.error("ServiceTitan authentication failed", error=str(e))
            raise ProviderAPIError(
                "servicetitan", 500, f"Authentication error: {str(e)}"
            )

    def get_auth_headers(self) -> dict:
        """Get headers with current access token."""
        if not self.access_token:
            raise ProviderAPIError("servicetitan", 401, "No access token available")

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
