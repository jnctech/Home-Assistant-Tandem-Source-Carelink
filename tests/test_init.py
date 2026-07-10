"""Tests for the Carelink integration __init__ module."""

from datetime import datetime

from custom_components.tandem import (
    convert_date_to_isodate,
    sanitize_for_logging,
)


class TestSanitizeForLogging:
    """Tests for the sanitize_for_logging function."""

    def test_sanitize_simple_dict(self):
        """Test sanitizing a simple dictionary with PII."""
        data = {"firstName": "John", "lastName": "Doe", "pumpBatteryLevel": 75}
        result = sanitize_for_logging(data)

        assert result["firstName"] == "[REDACTED]"
        assert result["lastName"] == "[REDACTED]"
        assert result["pumpBatteryLevel"] == 75

    def test_sanitize_nested_dict(self):
        """Test sanitizing nested dictionaries."""
        data = {
            "user": {
                "firstName": "John",
                "email": "john@example.com",
                "settings": {"theme": "dark"},
            }
        }
        result = sanitize_for_logging(data)

        assert result["user"]["firstName"] == "[REDACTED]"
        assert result["user"]["email"] == "[REDACTED]"
        assert result["user"]["settings"]["theme"] == "dark"

    def test_sanitize_list(self):
        """Test sanitizing a list containing dictionaries."""
        data = [
            {"firstName": "John", "status": "active"},
            {"firstName": "Jane", "status": "inactive"},
        ]
        result = sanitize_for_logging(data)

        assert result[0]["firstName"] == "[REDACTED]"
        assert result[0]["status"] == "active"
        assert result[1]["firstName"] == "[REDACTED]"
        assert result[1]["status"] == "inactive"

    def test_sanitize_max_depth(self):
        """Test that max depth prevents infinite recursion."""
        # Create deeply nested structure
        data = {"level": 0}
        current = data
        for i in range(15):
            current["nested"] = {"level": i + 1}
            current = current["nested"]

        result = sanitize_for_logging(data)
        # Should not raise an error and should handle deep nesting
        assert result is not None

    def test_sanitize_all_pii_fields(self):
        """Test that all known PII fields are redacted."""
        data = {
            "firstName": "John",
            "lastName": "Doe",
            "name": "John Doe",
            "birthdate": "1990-01-01",
            "username": "johndoe",
            "patientId": "12345",
            "conduitSerialNumber": "ABC123",
            "medicalDeviceSerialNumber": "XYZ789",
            "systemId": "SYS001",
            "email": "john@example.com",
            "phone": "555-1234",
            "emailAddress": "john@test.com",
            "phoneNumber": "555-5678",
            "address": "123 Main St",
            "dateOfBirth": "1990-01-01",
            "dob": "1990-01-01",
            "deviceSerialNumber": "DEV123",
        }
        result = sanitize_for_logging(data)

        for key in data.keys():
            assert result[key] == "[REDACTED]"

    def test_sanitize_non_dict_values(self):
        """Test sanitizing preserves non-dict values."""
        data = {"label": "test", "count": 42, "active": True, "rate": 1.5}
        result = sanitize_for_logging(data)

        assert result["label"] == "test"
        assert result["count"] == 42
        assert result["active"] is True
        assert result["rate"] == 1.5


class TestConvertDateToIsodate:
    """Tests for the convert_date_to_isodate function."""

    def test_convert_standard_format(self):
        """Test converting standard ISO format with milliseconds."""
        date_str = "2024-01-15T12:00:00.000Z"
        result = convert_date_to_isodate(date_str)

        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 12
        assert result.minute == 0
        assert result.second == 0
        assert result.tzinfo is None

    def test_convert_different_milliseconds(self):
        """Test converting with different millisecond values."""
        date_str = "2024-06-20T15:30:45.123Z"
        result = convert_date_to_isodate(date_str)

        assert result.year == 2024
        assert result.month == 6
        assert result.day == 20
        assert result.hour == 15
        assert result.minute == 30
        assert result.second == 45

    def test_convert_non_utc_positive_offset(self):
        """Non-UTC positive offset is normalised to UTC before stripping tzinfo (H7)."""
        # 12:00:00+05:30 → 06:30:00 UTC
        result = convert_date_to_isodate("2024-01-15T12:00:00+05:30")
        assert result.tzinfo is None
        assert result.hour == 6
        assert result.minute == 30

    def test_convert_non_utc_negative_offset(self):
        """Non-UTC negative offset is normalised to UTC before stripping tzinfo (H7)."""
        # 10:00:00-05:00 → 15:00:00 UTC
        result = convert_date_to_isodate("2024-01-15T10:00:00-05:00")
        assert result.tzinfo is None
        assert result.hour == 15
        assert result.minute == 0

    def test_convert_utc_zero_offset(self):
        """Explicit +00:00 offset produces the same UTC result as .000Z format."""
        result_z = convert_date_to_isodate("2024-03-01T08:00:00.000Z")
        result_plus = convert_date_to_isodate("2024-03-01T08:00:00+00:00")
        assert result_z == result_plus
