"""Tests for API utility functions."""

import pytest

from magentic_marketplace.api.utils import validate_schema_name


class TestValidateSchemaName:
    """Tests for schema name validation."""

    def test_valid_names(self):
        """Test that valid schema names are accepted."""
        valid_names = [
            "marketplace_10_5_1234567890",
            "test_experiment",
            "experiment123",
            "my_test_exp",
            "_private_schema",
            "a",
            "A",
            "_",
        ]
        for name in valid_names:
            assert validate_schema_name(name), f"Expected '{name}' to be valid"

    def test_invalid_names(self):
        """Test that invalid schema names are rejected."""
        invalid_names = [
            "",  # Empty
            "123invalid",  # Starts with digit
            "test-experiment",  # Contains hyphen
            "test.experiment",  # Contains dot
            "test experiment",  # Contains space
            "test;DROP TABLE",  # SQL injection attempt
            "test'experiment",  # Contains quote
            "test\"experiment",  # Contains double quote
            "test/experiment",  # Contains slash
            "test\\experiment",  # Contains backslash
            "test$experiment",  # Contains dollar sign
            "test@experiment",  # Contains at sign
            "test!experiment",  # Contains exclamation
            "test#experiment",  # Contains hash
            "test%experiment",  # Contains percent
        ]
        for name in invalid_names:
            assert not validate_schema_name(name), f"Expected '{name}' to be invalid"

    def test_none_and_empty(self):
        """Test that None and empty strings are rejected."""
        assert not validate_schema_name("")
        assert not validate_schema_name(None)  # type: ignore
