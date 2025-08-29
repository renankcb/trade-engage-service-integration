"""
Unit tests for value objects.
"""

import dataclasses

import pytest

from src.domain.value_objects.address import Address
from src.domain.value_objects.homeowner import Homeowner
from src.domain.value_objects.provider_type import ProviderType
from src.domain.value_objects.sync_status import SyncStatus


class TestSyncStatus:
    """Test SyncStatus value object."""

    def test_enum_values(self):
        """Test that all expected enum values exist."""
        expected_values = ["pending", "processing", "synced", "failed", "completed"]
        actual_values = [status.value for status in SyncStatus]
        assert actual_values == expected_values

    def test_can_retry(self):
        """Test can_retry method for all statuses."""
        # Statuses that can be retried
        assert SyncStatus.PENDING.can_retry() is True
        assert SyncStatus.FAILED.can_retry() is True

        # Statuses that cannot be retried
        assert SyncStatus.PROCESSING.can_retry() is False
        assert SyncStatus.SYNCED.can_retry() is False
        assert SyncStatus.COMPLETED.can_retry() is False

    def test_is_final(self):
        """Test is_final method for all statuses."""
        # Final statuses
        assert SyncStatus.COMPLETED.is_final() is True

        # Non-final statuses
        assert SyncStatus.PENDING.is_final() is False
        assert SyncStatus.PROCESSING.is_final() is False
        assert SyncStatus.SYNCED.is_final() is False
        assert SyncStatus.FAILED.is_final() is False

    def test_is_active(self):
        """Test is_active method for all statuses."""
        # Active statuses (require monitoring)
        assert SyncStatus.SYNCED.is_active() is True

        # Non-active statuses
        assert SyncStatus.PENDING.is_active() is False
        assert SyncStatus.PROCESSING.is_active() is False
        assert SyncStatus.FAILED.is_active() is False
        assert SyncStatus.COMPLETED.is_active() is False

    def test_can_be_claimed(self):
        """Test can_be_claimed method for all statuses."""
        # Statuses that can be claimed
        assert SyncStatus.PENDING.can_be_claimed() is True
        assert SyncStatus.FAILED.can_be_claimed() is True

        # Statuses that cannot be claimed
        assert SyncStatus.PROCESSING.can_be_claimed() is False
        assert SyncStatus.SYNCED.can_be_claimed() is False
        assert SyncStatus.COMPLETED.can_be_claimed() is False

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert SyncStatus.PENDING.value == "pending"
        assert SyncStatus.PROCESSING.value == "processing"
        assert SyncStatus.SYNCED.value == "synced"
        assert SyncStatus.FAILED.value == "failed"
        assert SyncStatus.COMPLETED.value == "completed"

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        assert SyncStatus.PENDING == "pending"
        assert SyncStatus.PENDING != "failed"
        assert SyncStatus.PENDING in ["pending", "failed"]
        assert SyncStatus.PROCESSING not in ["pending", "failed"]

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        statuses = list(SyncStatus)
        assert len(statuses) == 5
        assert all(isinstance(status, SyncStatus) for status in statuses)


class TestProviderType:
    """Test ProviderType value object."""

    def test_enum_values(self):
        """Test that all expected enum values exist."""
        expected_values = ["servicetitan", "housecallpro", "mock"]
        actual_values = [provider.value for provider in ProviderType]
        assert actual_values == expected_values

    def test_display_name(self):
        """Test display_name property for all providers."""
        assert ProviderType.SERVICETITAN.display_name == "ServiceTitan"
        assert ProviderType.HOUSECALLPRO.display_name == "HousecallPro"
        assert ProviderType.MOCK.display_name == "Mock Provider"

    def test_requires_auth(self):
        """Test requires_auth property for all providers."""
        # Providers that require authentication
        assert ProviderType.SERVICETITAN.requires_auth is True
        assert ProviderType.HOUSECALLPRO.requires_auth is True

        # Providers that don't require authentication
        assert ProviderType.MOCK.requires_auth is False

    def test_supports_webhooks(self):
        """Test supports_webhooks property for all providers."""
        # Providers that support webhooks
        assert ProviderType.HOUSECALLPRO.supports_webhooks is True
        assert ProviderType.MOCK.supports_webhooks is True

        # Providers that don't support webhooks
        assert ProviderType.SERVICETITAN.supports_webhooks is False

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert ProviderType.SERVICETITAN.value == "servicetitan"
        assert ProviderType.HOUSECALLPRO.value == "housecallpro"
        assert ProviderType.MOCK.value == "mock"

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        assert ProviderType.SERVICETITAN == "servicetitan"
        assert ProviderType.SERVICETITAN != "mock"
        assert ProviderType.HOUSECALLPRO in ["servicetitan", "housecallpro"]
        assert ProviderType.MOCK not in ["servicetitan", "housecallpro"]

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        providers = list(ProviderType)
        assert len(providers) == 3
        assert all(isinstance(provider, ProviderType) for provider in providers)

    def test_provider_characteristics(self):
        """Test comprehensive provider characteristics."""
        # ServiceTitan characteristics
        assert ProviderType.SERVICETITAN.value == "servicetitan"
        assert ProviderType.SERVICETITAN.display_name == "ServiceTitan"
        assert ProviderType.SERVICETITAN.requires_auth is True
        assert ProviderType.SERVICETITAN.supports_webhooks is False

        # HousecallPro characteristics
        assert ProviderType.HOUSECALLPRO.value == "housecallpro"
        assert ProviderType.HOUSECALLPRO.display_name == "HousecallPro"
        assert ProviderType.HOUSECALLPRO.requires_auth is True
        assert ProviderType.HOUSECALLPRO.supports_webhooks is True

        # Mock characteristics
        assert ProviderType.MOCK.value == "mock"
        assert ProviderType.MOCK.display_name == "Mock Provider"
        assert ProviderType.MOCK.requires_auth is False
        assert ProviderType.MOCK.supports_webhooks is True


class TestAddress:
    """Test Address value object."""

    def test_valid_address_creation(self):
        """Test valid address creation with all fields."""
        address = Address(
            street="123 Main St", city="Anytown", state="CA", zip_code="90210"
        )
        assert address.street == "123 Main St"
        assert address.city == "Anytown"
        assert address.state == "CA"
        assert address.zip_code == "90210"

    def test_full_address_property(self):
        """Test full_address property formatting."""
        address = Address(
            street="123 Main St", city="Anytown", state="CA", zip_code="90210"
        )
        expected = "123 Main St, Anytown, CA 90210"
        assert address.full_address == expected

    def test_to_dict_method(self):
        """Test to_dict method returns correct structure."""
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

    def test_validation_street_required(self):
        """Test validation that street is required."""
        with pytest.raises(ValueError, match="Street is required"):
            Address(street="", city="Anytown", state="CA", zip_code="90210")

        with pytest.raises(ValueError, match="Street is required"):
            Address(street="   ", city="Anytown", state="CA", zip_code="90210")

        with pytest.raises(ValueError, match="Street is required"):
            Address(street=None, city="Anytown", state="CA", zip_code="90210")

    def test_validation_city_required(self):
        """Test validation that city is required."""
        with pytest.raises(ValueError, match="City is required"):
            Address(street="123 Main St", city="", state="CA", zip_code="90210")

        with pytest.raises(ValueError, match="City is required"):
            Address(street="123 Main St", city="   ", state="CA", zip_code="90210")

        with pytest.raises(ValueError, match="City is required"):
            Address(street="123 Main St", city=None, state="CA", zip_code="90210")

    def test_validation_state_length(self):
        """Test validation that state must be exactly 2 characters."""
        with pytest.raises(ValueError, match="State must be 2 characters"):
            Address(
                street="123 Main St",
                city="Anytown",
                state="California",
                zip_code="90210",
            )

        with pytest.raises(ValueError, match="State must be 2 characters"):
            Address(
                street="123 Main St",
                city="Anytown",
                state="C",
                zip_code="90210",
            )

        with pytest.raises(ValueError, match="State must be 2 characters"):
            Address(
                street="123 Main St",
                city="Anytown",
                state="",
                zip_code="90210",
            )

    def test_validation_zip_code_required(self):
        """Test validation that zip code is required."""
        with pytest.raises(ValueError, match="ZIP code is required"):
            Address(street="123 Main St", city="Anytown", state="CA", zip_code="")

        with pytest.raises(ValueError, match="ZIP code is required"):
            Address(street="123 Main St", city="Anytown", state="CA", zip_code="   ")

        with pytest.raises(ValueError, match="ZIP code is required"):
            Address(street="123 Main St", city="Anytown", state="CA", zip_code=None)

    def test_address_with_whitespace(self):
        """Test address creation with leading/trailing whitespace."""
        address = Address(
            street="  123 Main St  ",
            city="  Anytown  ",
            state="CA",
            zip_code="  90210  ",
        )
        assert address.street == "  123 Main St  "
        assert address.city == "  Anytown  "
        assert address.state == "CA"
        assert address.zip_code == "  90210  "

    def test_address_immutability(self):
        """Test that Address objects are immutable (frozen)."""
        address = Address(
            street="123 Main St", city="Anytown", state="CA", zip_code="90210"
        )

        # Should not be able to modify attributes
        with pytest.raises(dataclasses.FrozenInstanceError):
            address.street = "456 Oak Ave"

    def test_address_equality(self):
        """Test address equality comparison."""
        address1 = Address(
            street="123 Main St", city="Anytown", state="CA", zip_code="90210"
        )
        address2 = Address(
            street="123 Main St", city="Anytown", state="CA", zip_code="90210"
        )
        address3 = Address(
            street="456 Oak Ave", city="Anytown", state="CA", zip_code="90210"
        )

        assert address1 == address2
        assert address1 != address3
        assert hash(address1) == hash(address2)
        assert hash(address1) != hash(address3)

    def test_address_hashable(self):
        """Test that Address objects are hashable."""
        address = Address(
            street="123 Main St", city="Anytown", state="CA", zip_code="90210"
        )

        # Should be able to use as dictionary key
        address_dict = {address: "test"}
        assert address in address_dict
        assert address_dict[address] == "test"

    def test_edge_cases(self):
        """Test edge cases for address creation."""
        # Very long street name
        long_street = "A" * 1000
        address = Address(
            street=long_street, city="Anytown", state="CA", zip_code="90210"
        )
        assert address.street == long_street

        # Special characters in address
        special_address = Address(
            street="123 Main St #4B", city="New York", state="NY", zip_code="10001"
        )
        assert special_address.street == "123 Main St #4B"
        assert special_address.city == "New York"


class TestHomeowner:
    """Test Homeowner value object."""

    def test_valid_homeowner_creation(self):
        """Test valid homeowner creation with all fields."""
        homeowner = Homeowner(
            name="John Doe", phone="555-1234", email="john@example.com"
        )
        assert homeowner.name == "John Doe"
        assert homeowner.phone == "555-1234"
        assert homeowner.email == "john@example.com"

    def test_homeowner_with_optional_fields(self):
        """Test homeowner creation with only required fields."""
        homeowner = Homeowner(name="Jane Smith")
        assert homeowner.name == "Jane Smith"
        assert homeowner.phone is None
        assert homeowner.email is None

    def test_homeowner_with_phone_only(self):
        """Test homeowner creation with name and phone only."""
        homeowner = Homeowner(name="Bob Johnson", phone="555-5678")
        assert homeowner.name == "Bob Johnson"
        assert homeowner.phone == "555-5678"
        assert homeowner.email is None

    def test_homeowner_with_email_only(self):
        """Test homeowner creation with name and email only."""
        homeowner = Homeowner(name="Alice Brown", email="alice@example.com")
        assert homeowner.name == "Alice Brown"
        assert homeowner.phone is None
        assert homeowner.email == "alice@example.com"

    def test_validation_name_required(self):
        """Test validation that name is required."""
        with pytest.raises(ValueError, match="Homeowner name is required"):
            Homeowner(name="")

        with pytest.raises(ValueError, match="Homeowner name is required"):
            Homeowner(name="   ")

        with pytest.raises(ValueError, match="Homeowner name is required"):
            Homeowner(name=None)

    def test_to_dict_method(self):
        """Test to_dict method returns correct structure."""
        homeowner = Homeowner(
            name="John Doe", phone="555-1234", email="john@example.com"
        )
        expected = {
            "name": "John Doe",
            "phone": "555-1234",
            "email": "john@example.com",
        }
        assert homeowner.to_dict() == expected

    def test_to_dict_with_optional_fields_none(self):
        """Test to_dict method when optional fields are None."""
        homeowner = Homeowner(name="Jane Smith")
        expected = {
            "name": "Jane Smith",
            "phone": None,
            "email": None,
        }
        assert homeowner.to_dict() == expected

    def test_homeowner_immutability(self):
        """Test that Homeowner objects are immutable (frozen)."""
        homeowner = Homeowner(name="John Doe", phone="555-1234")

        # Should not be able to modify attributes
        with pytest.raises(dataclasses.FrozenInstanceError):
            homeowner.name = "Jane Smith"

    def test_homeowner_equality(self):
        """Test homeowner equality comparison."""
        homeowner1 = Homeowner(name="John Doe", phone="555-1234")
        homeowner2 = Homeowner(name="John Doe", phone="555-1234")
        homeowner3 = Homeowner(name="Jane Smith", phone="555-1234")

        assert homeowner1 == homeowner2
        assert homeowner1 != homeowner3
        assert hash(homeowner1) == hash(homeowner2)
        assert hash(homeowner1) != hash(homeowner3)

    def test_homeowner_hashable(self):
        """Test that Homeowner objects are hashable."""
        homeowner = Homeowner(name="John Doe", phone="555-1234")

        # Should be able to use as dictionary key
        homeowner_dict = {homeowner: "test"}
        assert homeowner in homeowner_dict
        assert homeowner_dict[homeowner] == "test"

    def test_edge_cases(self):
        """Test edge cases for homeowner creation."""
        # Very long name
        long_name = "A" * 1000
        homeowner = Homeowner(name=long_name)
        assert homeowner.name == long_name

        # Special characters in name
        special_name = "José María O'Connor-Smith"
        homeowner = Homeowner(name=special_name)
        assert homeowner.name == special_name

        # Very long phone number
        long_phone = "1" * 50
        homeowner = Homeowner(name="John Doe", phone=long_phone)
        assert homeowner.phone == long_phone

        # Very long email
        long_email = "a" * 100 + "@example.com"
        homeowner = Homeowner(name="John Doe", email=long_email)
        assert homeowner.email == long_email

    def test_whitespace_handling(self):
        """Test how whitespace is handled in homeowner fields."""
        homeowner = Homeowner(name="  John Doe  ", phone="  555-1234  ")
        assert homeowner.name == "  John Doe  "
        assert homeowner.phone == "  555-1234  "

    def test_phone_formats(self):
        """Test various phone number formats."""
        phone_formats = [
            "555-1234",
            "(555) 123-4567",
            "555.123.4567",
            "555 123 4567",
            "+1-555-123-4567",
            "1-555-123-4567",
        ]

        for phone in phone_formats:
            homeowner = Homeowner(name="John Doe", phone=phone)
            assert homeowner.phone == phone

    def test_email_formats(self):
        """Test various email formats."""
        email_formats = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.com",
            "user@subdomain.example.com",
            "user@example.co.uk",
        ]

        for email in email_formats:
            homeowner = Homeowner(name="John Doe", email=email)
            assert homeowner.email == email
