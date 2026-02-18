"""Pydantic models for API request and response validation."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DatasetInfo(BaseModel):
    """Information about an available dataset."""

    name: str = Field(..., description="Dataset name")
    path: str = Field(..., description="Full path to dataset directory")
    num_businesses: int = Field(..., description="Number of business agents")
    num_customers: int = Field(..., description="Number of customer agents")


class ExperimentCreate(BaseModel):
    """Request model for creating a new experiment."""

    dataset: str = Field(..., description="Dataset name or path")
    experiment_name: str | None = Field(
        None, description="Optional experiment name (auto-generated if not provided)"
    )
    search_algorithm: str = Field("simple", description="Customer search strategy")
    search_bandwidth: int = Field(10, description="Search result limits")
    customer_max_steps: int | None = Field(
        None, description="Max agent steps before stopping"
    )
    postgres_host: str = Field("localhost", description="PostgreSQL host")
    postgres_port: int = Field(5432, description="PostgreSQL port")
    postgres_password: str = Field("postgres", description="PostgreSQL password")
    db_pool_min_size: int = Field(2, description="Database connection pool min size")
    db_pool_max_size: int = Field(10, description="Database connection pool max size")
    server_host: str = Field("127.0.0.1", description="Server host")
    server_port: int = Field(0, description="Server port (0 for auto-assign)")
    override: bool = Field(
        False, description="Override existing experiment with same name"
    )
    export_sqlite: bool = Field(False, description="Export results to SQLite")
    export_dir: str | None = Field(None, description="Directory for SQLite export")
    export_filename: str | None = Field(None, description="Filename for SQLite export")


class ExperimentStatus(BaseModel):
    """Status information for an experiment."""

    name: str = Field(..., description="Experiment name")
    status: Literal["pending", "running", "completed", "failed"] = Field(
        ..., description="Current experiment status"
    )
    started_at: datetime | None = Field(None, description="Start timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")
    error: str | None = Field(None, description="Error message if failed")


class ExperimentInfo(BaseModel):
    """Information about a stored experiment."""

    schema_name: str = Field(..., description="Experiment schema name")
    first_activity: datetime | None = Field(
        None, description="First agent registration timestamp"
    )
    last_activity: datetime | None = Field(None, description="Last activity timestamp")
    agents_count: int = Field(0, description="Number of agents")
    actions_count: int = Field(0, description="Number of actions")
    logs_count: int = Field(0, description="Number of logs")
    llm_providers: list[str] = Field(
        default_factory=list, description="LLM providers used"
    )


class SettingsResponse(BaseModel):
    """Current system settings and defaults."""

    default_search_algorithm: str = Field(
        "simple", description="Default search algorithm"
    )
    default_search_bandwidth: int = Field(10, description="Default search bandwidth")
    default_postgres_host: str = Field(
        "localhost", description="Default PostgreSQL host"
    )
    default_postgres_port: int = Field(5432, description="Default PostgreSQL port")
    available_providers: list[str] = Field(..., description="Available LLM providers")
