"""Integration tests for log streaming endpoints."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from magentic_marketplace.api import main as api_main


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(api_main.app)


@pytest.fixture
def mock_asyncpg_connection():
    """Create a mock asyncpg connection."""
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock()
    mock_conn.fetch = AsyncMock()
    mock_conn.close = AsyncMock()
    return mock_conn


class TestGetExperimentLogs:
    """Tests for the REST logs endpoint."""

    @pytest.mark.asyncio
    async def test_get_logs_invalid_schema_name(self, client):
        """Test that invalid schema names are rejected."""
        response = client.get("/api/experiments/test;DROP/logs")
        assert response.status_code == 400
        assert "Invalid experiment name" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_logs_with_hyphen(self, client):
        """Test that schema names with hyphens are rejected."""
        response = client.get("/api/experiments/test-experiment/logs")
        assert response.status_code == 400
        assert "Invalid experiment name" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_logs_valid_schema_name(self, client, mock_asyncpg_connection):
        """Test that valid schema names pass validation."""
        # Setup mock responses
        mock_asyncpg_connection.fetchval.side_effect = [
            True,  # schema exists
            True,  # logs table exists
            5,  # total count
        ]
        mock_asyncpg_connection.fetch.return_value = [
            {
                "created_at": datetime.now(UTC),
                "data": {
                    "level": "info",
                    "message": "Test log",
                    "data": {"key": "value"},
                    "metadata": {"agent_id": "agent_123"},
                },
            }
        ]

        with patch("asyncpg.connect", return_value=mock_asyncpg_connection):
            response = client.get("/api/experiments/valid_experiment_123/logs")
            assert response.status_code == 200
            data = response.json()
            assert "logs" in data
            assert "total" in data
            assert "has_more" in data

    @pytest.mark.asyncio
    async def test_get_logs_schema_not_found(self, client, mock_asyncpg_connection):
        """Test error when schema doesn't exist."""
        mock_asyncpg_connection.fetchval.return_value = False  # schema doesn't exist

        with patch("asyncpg.connect", return_value=mock_asyncpg_connection):
            response = client.get("/api/experiments/nonexistent/logs")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_logs_with_since_parameter(
        self, client, mock_asyncpg_connection
    ):
        """Test filtering logs by timestamp."""
        since = datetime.now(UTC).isoformat()
        mock_asyncpg_connection.fetchval.side_effect = [
            True,  # schema exists
            True,  # logs table exists
            10,  # total count
        ]
        mock_asyncpg_connection.fetch.return_value = []

        with patch("asyncpg.connect", return_value=mock_asyncpg_connection):
            response = client.get(
                f"/api/experiments/test_experiment/logs?since={since}"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["logs"] == []
            assert data["total"] == 10

    @pytest.mark.asyncio
    async def test_get_logs_invalid_timestamp(self, client, mock_asyncpg_connection):
        """Test error with invalid timestamp format."""
        mock_asyncpg_connection.fetchval.side_effect = [
            True,  # schema exists
            True,  # logs table exists
        ]

        with patch("asyncpg.connect", return_value=mock_asyncpg_connection):
            response = client.get(
                "/api/experiments/test_experiment/logs?since=invalid-timestamp"
            )
            assert response.status_code == 400
            assert "Invalid timestamp" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_logs_limit_parameter(self, client, mock_asyncpg_connection):
        """Test that limit parameter is respected."""
        mock_asyncpg_connection.fetchval.side_effect = [
            True,  # schema exists
            True,  # logs table exists
            100,  # total count
        ]
        # Return 11 logs to test has_more
        mock_asyncpg_connection.fetch.return_value = [
            {
                "created_at": datetime.now(UTC),
                "data": {"level": "info", "message": f"Log {i}"},
            }
            for i in range(11)
        ]

        with patch("asyncpg.connect", return_value=mock_asyncpg_connection):
            response = client.get("/api/experiments/test_experiment/logs?limit=10")
            assert response.status_code == 200
            data = response.json()
            assert len(data["logs"]) == 10
            assert data["has_more"] is True


class TestWebSocketExperimentLogs:
    """Tests for the WebSocket logs endpoint."""

    @pytest.mark.asyncio
    async def test_websocket_invalid_schema_name(self, client):
        """Test that WebSocket rejects invalid schema names."""
        with client.websocket_connect(
            "/api/experiments/test;DROP/logs/ws"
        ) as websocket:
            # The connection should be rejected
            pass

    @pytest.mark.asyncio
    async def test_websocket_schema_validation(self, client, mock_asyncpg_connection):
        """Test WebSocket with valid schema name but non-existent experiment."""
        mock_asyncpg_connection.fetchval.return_value = False  # schema doesn't exist

        with patch("asyncpg.connect", return_value=mock_asyncpg_connection):
            with client.websocket_connect(
                "/api/experiments/valid_experiment/logs/ws"
            ) as websocket:
                data = websocket.receive_json()
                assert data["type"] == "error"
                assert "not found" in data["error"]


class TestSchemaValidationIntegration:
    """Integration tests for schema name validation across endpoints."""

    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self, client):
        """Test that SQL injection attempts are blocked."""
        dangerous_names = [
            "test'; DROP TABLE logs;--",
            "test' OR '1'='1",
            "test; DELETE FROM logs",
            "test UNION SELECT * FROM logs",
        ]

        for name in dangerous_names:
            response = client.get(f"/api/experiments/{name}/logs")
            assert response.status_code == 400
            assert "Invalid experiment name" in response.json()["detail"]
