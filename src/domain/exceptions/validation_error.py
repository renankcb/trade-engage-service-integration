"""
Validation-related domain exceptions.
"""


class ValidationError(Exception):
    """Base exception for validation errors."""

    pass


class RequiredFieldError(ValidationError):
    """Raised when required field is missing."""

    def __init__(self, field_name: str):
        self.field_name = field_name
        super().__init__(f"Required field '{field_name}' is missing")


class InvalidFormatError(ValidationError):
    """Raised when field format is invalid."""

    def __init__(self, field_name: str, expected_format: str):
        self.field_name = field_name
        self.expected_format = expected_format
        super().__init__(
            f"Field '{field_name}' has invalid format, expected: {expected_format}"
        )
