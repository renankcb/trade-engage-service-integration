"""
ServiceTitan data transformer.
"""

from typing import Any, Dict

from src.application.interfaces.providers import CreateLeadRequest, CreateLeadResponse
from src.infrastructure.providers.servicetitan.models import (
    ServiceTitanLeadRequest,
    ServiceTitanLeadResponse,
    ServiceTitanStatusResponse,
)


class ServiceTitanTransformer:
    """Transform data between domain and ServiceTitan formats."""

    def transform_lead_request(
        self, lead_data: CreateLeadRequest
    ) -> ServiceTitanLeadRequest:
        """Transform domain lead request to ServiceTitan format."""
        return ServiceTitanLeadRequest(
            summary=lead_data.job.summary,
            customer_name=lead_data.job.homeowner_name,
            customer_phone=lead_data.job.homeowner_phone,
            customer_email=lead_data.job.homeowner_email,
            address=lead_data.job.address.street,
            city=lead_data.job.address.city,
            state=lead_data.job.address.state,
            zip_code=lead_data.job.address.zip_code,
            priority="normal",
            notes=None,
        )

    def transform_lead_response(
        self, response: ServiceTitanLeadResponse
    ) -> CreateLeadResponse:
        """Transform ServiceTitan response to domain format."""
        return CreateLeadResponse(
            success=True,
            external_id=response.id,
            status=response.status,
            created_at=response.created_at,
            customer_id=response.customer_id,
            location_id=response.location_id,
        )

    def transform_status_response(
        self, response: ServiceTitanStatusResponse
    ) -> Dict[str, Any]:
        """Transform ServiceTitan status response to domain format."""
        return {
            "external_id": response.id,
            "status": response.status,
            "is_completed": response.is_completed,
            "revenue": response.revenue,
            "completed_at": response.completed_at,
            "notes": response.notes,
        }

    def transform_update_request(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform domain update data to ServiceTitan format."""
        transformed = {}

        # Map common fields
        if "summary" in update_data:
            transformed["summary"] = update_data["summary"]

        if "priority" in update_data:
            transformed["priority"] = update_data["priority"]

        if "notes" in update_data:
            transformed["notes"] = update_data["notes"]

        if "status" in update_data:
            transformed["status"] = update_data["status"]

        # Handle customer updates
        if "homeowner" in update_data:
            homeowner = update_data["homeowner"]
            if "name" in homeowner:
                transformed["customerName"] = homeowner["name"]
            if "phone" in homeowner:
                transformed["customerPhone"] = homeowner["phone"]
            if "email" in homeowner:
                transformed["customerEmail"] = homeowner["email"]

        # Handle address updates
        if "address" in update_data:
            address = update_data["address"]
            if "street" in address:
                transformed["address"] = address["street"]
            if "city" in address:
                transformed["city"] = address["city"]
            if "state" in address:
                transformed["state"] = address["state"]
            if "zip_code" in address:
                transformed["zipCode"] = address["zip_code"]

        return transformed

    def transform_job_to_lead(
        self, job_data: Dict[str, Any]
    ) -> ServiceTitanLeadRequest:
        """Transform job data to ServiceTitan lead format."""
        return ServiceTitanLeadRequest(
            summary=job_data.get("summary", ""),
            customer_name=job_data.get("homeowner_name", ""),
            customer_phone=job_data.get("homeowner_phone", ""),
            customer_email=job_data.get("homeowner_email", ""),
            address=job_data.get("street", ""),
            city=job_data.get("city", ""),
            state=job_data.get("state", ""),
            zip_code=job_data.get("zip_code", ""),
            priority=job_data.get("priority", "normal"),
            notes=job_data.get("notes"),
        )

    def transform_lead_to_job(
        self, lead_data: ServiceTitanLeadResponse
    ) -> Dict[str, Any]:
        """Transform ServiceTitan lead to job format."""
        return {
            "external_id": lead_data.id,
            "status": lead_data.status,
            "created_at": lead_data.created_at,
            "customer_id": lead_data.customer_id,
            "location_id": lead_data.location_id,
            "summary": lead_data.summary,
        }
