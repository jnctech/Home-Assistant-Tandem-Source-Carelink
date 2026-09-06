"""Exceptions for the Tandem integration."""

from __future__ import annotations


class TandemApiError(Exception):
    """Raised when the Tandem Source API returns an error or unexpected data."""


class TandemAuthError(TandemApiError):
    """Raised when authentication with the Tandem Source API fails."""
