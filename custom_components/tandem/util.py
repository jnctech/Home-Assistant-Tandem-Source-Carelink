"""Shared utilities for the Tandem integration (logging redaction, date parsing)."""

from __future__ import annotations

import re
from datetime import datetime, timezone

# Fields containing personally identifiable information that should be redacted.
# Note: "name" is intentionally broad — it catches pumper_info.name (full name)
# and profile[].name (often the patient's first name). This over-redacts
# non-PII profile names like "Sick" or "Active", but PII protection takes
# priority.  Profile idp index is sufficient for debugging.
PII_FIELDS = {
    "firstName",
    "lastName",
    "name",
    "birthdate",
    "username",
    "patientId",
    "conduitSerialNumber",
    "medicalDeviceSerialNumber",
    "systemId",
    "email",
    "phone",
    "emailAddress",
    "phoneNumber",
    "address",
    "dateOfBirth",
    "dob",
    "deviceSerialNumber",
    "patientName",
    "patientDateOfBirth",
    "patientCareGiver",
}


def sanitize_for_logging(data, depth=0):
    """Recursively sanitize data by redacting PII fields for safe logging."""
    if depth > 10:  # Prevent infinite recursion
        return "[MAX_DEPTH]"
    if isinstance(data, dict):
        return {k: "[REDACTED]" if k in PII_FIELDS else sanitize_for_logging(v, depth + 1) for k, v in data.items()}
    if isinstance(data, list):
        return [sanitize_for_logging(item, depth + 1) for item in data]
    return data


def convert_date_to_isodate(date):
    date_iso = re.sub(r"\.\d{3}Z$", "+00:00", date)
    dt = datetime.fromisoformat(date_iso)
    # Normalize any UTC offset to UTC before stripping tzinfo so the resulting
    # naive datetime always represents UTC, regardless of what offset the API sent.
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
