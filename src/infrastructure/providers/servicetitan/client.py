"""
ServiceTitan API client.
"""

import time
from typing import Optional, Dict, Any
import httpx
import structlog
from src.domain.exceptions.provider_error import ProviderAPIError
from src.infrastructure.providers.servicetitan.auth import ServiceTitanAuth
from src.infrastructure.providers.servicetitan.models import (
    ServiceTitanLeadRequest,
    ServiceTitanLeadResponse,
    ServiceTitanStatusResponse
)

logger = structlog.get_logger()


class ServiceTitanClient:
    """ServiceTitan API client."""
    
    def __init__(self, client_id: str, client_secret: str, tenant_id: str):
        self.auth = ServiceTitanAuth(client_id, client_secret, tenant_id)
        self.base_url = f"https://api.servicetitan.com/v2/tenant/{tenant_id}"
        self.timeout = 30.0
    
    async def create_lead(self, lead_data: ServiceTitanLeadRequest) -> ServiceTitanLeadResponse:
        """Create a lead in ServiceTitan."""
        try:
            # Get authentication headers
            headers = await self._get_auth_headers()
            
            # Prepare request data
            request_data = {
                "summary": lead_data.summary,
                "customer": {
                    "name": lead_data.customer_name,
                    "phone": lead_data.customer_phone,
                    "email": lead_data.customer_email
                },
                "location": {
                    "address": lead_data.address,
                    "city": lead_data.city,
                    "state": lead_data.state,
                    "zipCode": lead_data.zip_code
                },
                "priority": lead_data.priority,
                "notes": lead_data.notes
            }
            
            # Make API request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/leads",
                    json=request_data,
                    headers=headers
                )
                
                if response.status_code != 201:
                    raise ProviderAPIError(
                        "servicetitan",
                        response.status_code,
                        f"Failed to create lead: {response.text}"
                    )
                
                response_data = response.json()
                
                return ServiceTitanLeadResponse(
                    id=str(response_data["id"]),
                    status=response_data["status"],
                    created_at=response_data["createdAt"],
                    customer_id=str(response_data["customerId"]),
                    location_id=str(response_data["locationId"])
                )
                
        except httpx.TimeoutException:
            raise ProviderAPIError(
                "servicetitan", 
                408, 
                "Request timeout"
            )
        except httpx.RequestError as e:
            raise ProviderAPIError(
                "servicetitan", 
                0, 
                f"Network error: {str(e)}"
            )
        except Exception as e:
            logger.error(
                "Failed to create lead",
                error=str(e),
                client_id=self.auth.client_id
            )
            raise
    
    async def get_lead(self, lead_id: str) -> ServiceTitanStatusResponse:
        """Get lead status from ServiceTitan."""
        try:
            headers = await self._get_auth_headers()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/leads/{lead_id}",
                    headers=headers
                )
                
                if response.status_code != 200:
                    raise ProviderAPIError(
                        "servicetitan",
                        response.status_code,
                        f"Failed to get lead: {response.text}"
                    )
                
                response_data = response.json()
                
                return ServiceTitanStatusResponse(
                    id=str(response_data["id"]),
                    status=response_data["status"],
                    is_completed=response_data["status"] in ["Completed", "Closed"],
                    revenue=response_data.get("total"),
                    completed_at=response_data.get("completedOn"),
                    notes=response_data.get("notes")
                )
                
        except httpx.TimeoutException:
            raise ProviderAPIError(
                "servicetitan", 
                408, 
                "Request timeout"
            )
        except httpx.RequestError as e:
            raise ProviderAPIError(
                "servicetitan", 
                0, 
                f"Network error: {str(e)}"
            )
        except Exception as e:
            logger.error(
                "Failed to get lead",
                lead_id=lead_id,
                error=str(e)
            )
            raise ProviderAPIError(
                "servicetitan",
                500,
                f"Failed to get lead: {str(e)}"
            )
    
    async def update_lead(self, lead_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a lead in ServiceTitan."""
        try:
            headers = await self._get_auth_headers()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.patch(
                    f"{self.base_url}/leads/{lead_id}",
                    json=update_data,
                    headers=headers
                )
                
                if response.status_code != 200:
                    raise ProviderAPIError(
                        "servicetitan",
                        response.status_code,
                        f"Failed to update lead: {response.text}"
                    )
                
                logger.info(
                    "Lead updated successfully",
                    lead_id=lead_id
                )
                
                return True
                
        except httpx.TimeoutException:
            raise ProviderAPIError(
                "servicetitan", 
                408, 
                "Request timeout"
            )
        except httpx.RequestError as e:
            raise ProviderAPIError(
                "servicetitan", 
                0, 
                f"Network error: {str(e)}"
            )
        except Exception as e:
            logger.error(
                "Failed to update lead",
                lead_id=lead_id,
                error=str(e)
            )
            raise ProviderAPIError(
                "servicetitan",
                500,
                f"Failed to update lead: {str(e)}"
            )
    
    async def test_connection(self) -> float:
        """Test API connectivity and return response time."""
        start_time = time.time()
        
        try:
            headers = await self._get_auth_headers()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/company",
                    headers=headers
                )
                
                if response.status_code != 200:
                    raise ProviderAPIError(
                        "servicetitan",
                        response.status_code,
                        "Connection test failed"
                    )
                
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                
                logger.info(
                    "ServiceTitan connection test successful",
                    response_time_ms=response_time
                )
                
                return response_time
                
        except Exception as e:
            logger.error(
                "ServiceTitan connection test failed",
                error=str(e)
            )
            raise
    
    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers with valid token."""
        access_token = await self.auth.get_access_token()
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
