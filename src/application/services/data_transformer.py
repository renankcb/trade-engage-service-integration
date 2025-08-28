"""Data transformation service."""

from typing import Any, Dict

from src.config.logging import get_logger
from src.domain.entities.job import Job
from src.domain.value_objects.provider_type import ProviderType

logger = get_logger(__name__)


class DataTransformer:
    """Transforms data between internal and provider formats."""

    def transform_job_to_provider(
        self, job: Job, provider_type: ProviderType, company_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform job data to provider-specific format."""

        base_data = job.to_provider_format()

        if provider_type == ProviderType.SERVICETITAN:
            return self._transform_to_servicetitan(base_data, company_config)
        elif provider_type == ProviderType.HOUSECALLPRO:
            return self._transform_to_housecallpro(base_data, company_config)
        elif provider_type == ProviderType.MOCK:
            return base_data
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

    def _transform_to_servicetitan(
        self, data: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform to ServiceTitan format."""
        return {
            "summary": data["description"],
            "customerId": None,  # Will be created
            "locationId": None,  # Will be created
            "jobTypeId": config.get("default_job_type_id", 1),
            "priority": "Normal",
            "customerInfo": {
                "firstName": data["customer_name"].split(" ")[0]
                if data["customer_name"]
                else "Unknown",
                "lastName": " ".join(data["customer_name"].split(" ")[1:])
                if data["customer_name"]
                else "Customer",
                "phoneNumber": data.get("customer_phone", ""),
                "email": data.get("customer_email", ""),
            },
            "serviceAddress": {
                "street": data["service_address"]["street"],
                "city": data["service_address"]["city"],
                "state": data["service_address"]["state"],
                "zip": data["service_address"]["zip_code"],
                "country": "USA",
            },
            "businessUnitId": config.get("business_unit_id", 1),
        }

    def _transform_to_housecallpro(
        self, data: Dict[str, Any], config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform to HousecallPro format."""
        return {
            "work_order": {
                "description": data["description"],
                "customer": {
                    "first_name": data["customer_name"].split(" ")[0]
                    if data["customer_name"]
                    else "Unknown",
                    "last_name": " ".join(data["customer_name"].split(" ")[1:])
                    if data["customer_name"]
                    else "Customer",
                    "mobile_number": data.get("customer_phone", ""),
                    "email": data.get("customer_email", ""),
                    "address": {
                        "street": data["service_address"]["street"],
                        "city": data["service_address"]["city"],
                        "state": data["service_address"]["state"],
                        "zip": data["service_address"]["zip_code"],
                    },
                },
                "employee_ids": config.get("default_employee_ids", []),
                "tags": ["TradeEngage"],
            }
        }

    def parse_provider_response(
        self, response_data: Dict[str, Any], provider_type: ProviderType
    ) -> Dict[str, Any]:
        """Parse provider response to standard format."""

        if provider_type == ProviderType.SERVICETITAN:
            return self._parse_servicetitan_response(response_data)
        elif provider_type == ProviderType.HOUSECALLPRO:
            return self._parse_housecallpro_response(response_data)
        else:
            return response_data

    def _parse_servicetitan_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse ServiceTitan response."""
        return {
            "external_id": str(data.get("id", "")),
            "status": data.get("status", "unknown"),
            "is_completed": data.get("status") == "Completed",
            "revenue": data.get("total", 0.0),
            "completed_at": data.get("completedOn"),
            "provider_data": data,
        }

    def _parse_housecallpro_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse HousecallPro response."""
        work_order = data.get("work_order", {})
        return {
            "external_id": str(work_order.get("id", "")),
            "status": work_order.get("work_status", "unknown"),
            "is_completed": work_order.get("work_status") == "Completed",
            "revenue": float(work_order.get("outstanding_balance", 0.0)),
            "completed_at": work_order.get("completed_at"),
            "provider_data": data,
        }
