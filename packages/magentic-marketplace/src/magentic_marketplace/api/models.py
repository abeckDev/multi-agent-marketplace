"""Pydantic models for API request and response validation."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DatasetInfo(BaseModel):
    """Information about an available dataset."""

    name: str = Field(..., description="Dataset name", examples=["demo_small"])
    path: str = Field(
        ...,
        description="Full path to dataset directory",
        examples=["/home/user/multi-agent-marketplace/data/demo_small"],
    )
    num_businesses: int = Field(
        ..., description="Number of business agents", examples=[10]
    )
    num_customers: int = Field(
        ..., description="Number of customer agents", examples=[20]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "demo_small",
                    "path": "/home/user/multi-agent-marketplace/data/demo_small",
                    "num_businesses": 10,
                    "num_customers": 20,
                }
            ]
        }
    }


class ExperimentCreate(BaseModel):
    """Request model for creating a new experiment."""

    dataset: str = Field(
        ...,
        description="Dataset name or absolute path to dataset directory",
        examples=["demo_small"],
    )
    experiment_name: str | None = Field(
        None,
        description="Optional custom experiment name (auto-generated if not provided)",
        examples=["my_marketplace_experiment"],
    )
    search_algorithm: str = Field(
        "simple",
        description="Customer search strategy algorithm",
        examples=["simple"],
    )
    search_bandwidth: int = Field(
        10,
        description="Maximum number of search results to return per query",
        examples=[10],
        ge=1,
    )
    customer_max_steps: int | None = Field(
        None,
        description="Maximum agent steps before stopping (None for unlimited)",
        examples=[100],
        ge=1,
    )
    postgres_host: str = Field(
        "localhost",
        description="PostgreSQL server hostname",
        examples=["localhost"],
    )
    postgres_port: int = Field(
        5432, description="PostgreSQL server port", examples=[5432], ge=1, le=65535
    )
    postgres_password: str = Field(
        "postgres", description="PostgreSQL password", examples=["postgres"]
    )
    db_pool_min_size: int = Field(
        2,
        description="Database connection pool minimum size",
        examples=[2],
        ge=1,
    )
    db_pool_max_size: int = Field(
        10,
        description="Database connection pool maximum size",
        examples=[10],
        ge=1,
    )
    server_host: str = Field(
        "127.0.0.1", description="Simulation server host", examples=["127.0.0.1"]
    )
    server_port: int = Field(
        0,
        description="Simulation server port (0 for auto-assign)",
        examples=[0],
        ge=0,
        le=65535,
    )
    override: bool = Field(
        False,
        description="Override existing experiment with same name if it exists",
        examples=[False],
    )
    export_sqlite: bool = Field(
        False, description="Export experiment results to SQLite", examples=[False]
    )
    export_dir: str | None = Field(
        None,
        description="Directory for SQLite export (if export_sqlite=true)",
        examples=["./exports"],
    )
    export_filename: str | None = Field(
        None,
        description="Filename for SQLite export (if export_sqlite=true)",
        examples=["experiment_results.db"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "dataset": "demo_small",
                    "experiment_name": "my_first_experiment",
                    "search_algorithm": "simple",
                    "search_bandwidth": 10,
                    "customer_max_steps": 100,
                    "postgres_host": "localhost",
                    "postgres_port": 5432,
                    "postgres_password": "postgres",
                    "override": False,
                    "export_sqlite": False,
                }
            ]
        }
    }


class ExperimentStatus(BaseModel):
    """Status information for an experiment."""

    name: str = Field(..., description="Experiment name", examples=["my_experiment"])
    status: Literal["pending", "running", "completed", "failed"] = Field(
        ...,
        description="Current experiment status",
        examples=["running"],
    )
    started_at: datetime | None = Field(
        None,
        description="Timestamp when experiment started",
        examples=["2024-01-15T10:30:00Z"],
    )
    completed_at: datetime | None = Field(
        None,
        description="Timestamp when experiment completed or failed",
        examples=["2024-01-15T11:45:00Z"],
    )
    error: str | None = Field(
        None,
        description="Error message if experiment failed",
        examples=["Database connection failed"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "marketplace_20_10_1705318200000",
                    "status": "running",
                    "started_at": "2024-01-15T10:30:00Z",
                    "completed_at": None,
                    "error": None,
                }
            ]
        }
    }


class ExperimentInfo(BaseModel):
    """Information about a stored experiment in the database."""

    schema_name: str = Field(
        ...,
        description="Experiment schema name in PostgreSQL",
        examples=["marketplace_20_10_1705318200000"],
    )
    first_activity: datetime | None = Field(
        None,
        description="Timestamp of first agent registration",
        examples=["2024-01-15T10:30:00Z"],
    )
    last_activity: datetime | None = Field(
        None,
        description="Timestamp of last recorded activity",
        examples=["2024-01-15T11:45:00Z"],
    )
    agents_count: int = Field(
        0, description="Total number of agents in experiment", examples=[30]
    )
    actions_count: int = Field(
        0, description="Total number of actions logged", examples=[450]
    )
    logs_count: int = Field(
        0, description="Total number of log entries", examples=[1200]
    )
    llm_providers: list[str] = Field(
        default_factory=list,
        description="List of LLM providers used in this experiment",
        examples=[["openai", "anthropic"]],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "schema_name": "marketplace_20_10_1705318200000",
                    "first_activity": "2024-01-15T10:30:00Z",
                    "last_activity": "2024-01-15T11:45:00Z",
                    "agents_count": 30,
                    "actions_count": 450,
                    "logs_count": 1200,
                    "llm_providers": ["openai", "anthropic"],
                }
            ]
        }
    }


class SettingsResponse(BaseModel):
    """Current system settings and defaults."""

    default_search_algorithm: str = Field(
        "simple",
        description="Default customer search algorithm",
        examples=["simple"],
    )
    default_search_bandwidth: int = Field(
        10, description="Default maximum search results", examples=[10]
    )
    default_postgres_host: str = Field(
        "localhost", description="Default PostgreSQL hostname", examples=["localhost"]
    )
    default_postgres_port: int = Field(
        5432, description="Default PostgreSQL port", examples=[5432]
    )
    available_providers: list[str] = Field(
        ...,
        description="List of available LLM providers for experiments",
        examples=[["openai", "anthropic", "azure_openai", "google"]],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "default_search_algorithm": "simple",
                    "default_search_bandwidth": 10,
                    "default_postgres_host": "localhost",
                    "default_postgres_port": 5432,
                    "available_providers": [
                        "openai",
                        "anthropic",
                        "azure_openai",
                        "google",
                    ],
                }
            ]
        }
    }
