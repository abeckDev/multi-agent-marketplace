"""Utility functions for the API."""

import re


def validate_schema_name(name: str) -> bool:
    """Validate that a schema/experiment name is safe.

    Only alphanumeric characters and underscores are allowed to prevent
    SQL injection and accidental data exposure.

    Args:
        name: The schema/experiment name to validate

    Returns:
        True if the name is valid, False otherwise

    """
    if not name:
        return False
    # Only allow alphanumeric and underscore, must not start with a digit
    pattern = r"^[a-zA-Z_][a-zA-Z0-9_]*$"
    return bool(re.match(pattern, name))
