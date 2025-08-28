"""
Unit tests for value objects.
"""

import pytest

from src.domain.value_objects.address import Address
from src.domain.value_objects.provider_type import ProviderType
from src.domain.value_objects.sync_status import SyncStatus


class TestSyncStatus:
    """Test SyncStatus value object."""

    def test_can_retry(self):
        """Test can_retry method."""
        assert SyncStatus.PENDING.can_retry() is True
        assert SyncStatus.FAILED.can_retry() is True
        assert SyncStatus.SYNCED.can_retry() is False
        assert SyncStatus.COMPLETED.can_retry() is False

    def test_is_final(self):
        """Test is_final method."""
        assert SyncStatus.COMPLETED.is_final() is True
        assert SyncStatus.PENDING.is_final() is False
        assert SyncStatus.SYNCED.is_final() is False
        assert SyncStatus.FAILED.is_final() is False

    def test_is_active(self):
        """Test is_active method."""
        assert SyncStatus.SYNCED.is_active() is True
        assert SyncStatus.PENDING.is_active() is False
        assert SyncStatus.FAILED.is_active() is False
        assert SyncStatus.COMPLETED.is_active() is False


class TestProviderType:
    """Test ProviderType value object."""

    def test_display_name(self):
        """Test display_name property."""
        assert ProviderType.SERVICETITAN.display_name == "ServiceTitan"
        assert ProviderType.HOUSECALLPRO.display_name == "HousecallPro"
        assert ProviderType.MOCK.display_name == "Mock Provider"

    def test_requires_auth(self):
        """Test requires_auth property."""
        assert ProviderType.SERVICETITAN.requires_auth is True
        assert ProviderType.HOUSECALLPRO.requires_auth is True
        assert ProviderType.MOCK.requires_auth is False

    def test_supports_webhooks(self):
        """Test supports_webhooks property."""
        assert ProviderType.SERVICETITAN.supports_webhooks is False
        assert ProviderType.HOUSECALLPRO.supports_webhooks is True
        assert ProviderType.MOCK.supports_webhooks is True


class TestAddress:
    """Test Address value object."""

    def test_valid_address(self):
        """Test valid address creation."""
        address = Address(
            street="123 Main St", city="Anytown", state="CA", zip_code="90210"
        )
        assert address.street == "123 Main St"
        assert address.city == "Anytown"
        assert address.state == "CA"
        assert address.zip_code == "90210"

    def test_full_address(self):
        """Test full_address property."""
        address = Address(
            street="123 Main St", city="Anytown", state="CA", zip_code="90210"
        )
        expected = "123 Main St, Anytown, CA 90210"
        assert address.full_address == expected

    def test_invalid_street(self):
        """Test invalid street validation."""
        with pytest.raises(ValueError, match="Street is required"):
            Address(street="", city="Anytown", state="CA", zip_code="90210")

    def test_invalid_state(self):
        """Test invalid state validation."""
        with pytest.raises(ValueError, match="State must be 2 characters"):
            Address(
                street="123 Main St",
                city="Anytown",
                state="California",
                zip_code="90210",
            )

    def test_to_dict(self):
        """Test to_dict method."""
        address = Address(
            street="123 Main St", city="Anytown", state="CA", zip_code="90210"
        )
        expected = {
            "street": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "zip_code": "90210",
        }
        assert address.to_dict() == expected
