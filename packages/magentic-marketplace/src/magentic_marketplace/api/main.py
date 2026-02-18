"""FastAPI orchestrator API for launching and managing marketplace experiments.

This module provides REST API endpoints for:
- Listing available datasets
- Creating and running experiments in background
- Checking experiment status and progress
- Listing completed experiments from the database
- Retrieving current system settings
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

import asyncpg
from fastapi import BackgroundTasks, FastAPI, HTTPException

from magentic_marketplace.api.models import (
    DatasetInfo,
    ExperimentCreate,
    ExperimentInfo,
    ExperimentStatus,
    SettingsResponse,
)
from magentic_marketplace.experiments.run_experiment import run_marketplace_experiment
from magentic_marketplace.marketplace.llm.config import ALLOWED_LLM_PROVIDERS

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Magentic Marketplace Orchestrator API",
    description="API for launching and managing marketplace experiments",
    version="1.0.0",
)

# In-memory experiment tracking
experiment_tracker: dict[str, ExperimentStatus] = {}


def get_data_directory() -> Path:
    """Get the data directory path.

    Returns the path to the data directory containing datasets.
    """
    # Assume data directory is at the root of the repository
    api_path = Path(__file__).resolve()
    # Navigate from api/main.py -> magentic_marketplace -> src -> packages -> repo root
    repo_root = api_path.parent.parent.parent.parent.parent.parent
    data_dir = repo_root / "data"
    return data_dir


async def run_experiment_background(
    experiment_config: ExperimentCreate, experiment_name: str
):
    """Run an experiment in the background and update its status.

    Args:
        experiment_config: Configuration for the experiment
        experiment_name: Name of the experiment to track

    """
    try:
        # Update status to running
        experiment_tracker[experiment_name].status = "running"
        experiment_tracker[experiment_name].started_at = datetime.now(UTC)

        logger.info(f"Starting experiment: {experiment_name}")

        # Run the experiment
        await run_marketplace_experiment(
            data_dir=experiment_config.dataset,
            experiment_name=experiment_name,
            search_algorithm=experiment_config.search_algorithm,
            search_bandwidth=experiment_config.search_bandwidth,
            customer_max_steps=experiment_config.customer_max_steps,
            postgres_host=experiment_config.postgres_host,
            postgres_port=experiment_config.postgres_port,
            postgres_password=experiment_config.postgres_password,
            db_pool_min_size=experiment_config.db_pool_min_size,
            db_pool_max_size=experiment_config.db_pool_max_size,
            server_host=experiment_config.server_host,
            server_port=experiment_config.server_port,
            override=experiment_config.override,
            export_sqlite=experiment_config.export_sqlite,
            export_dir=experiment_config.export_dir,
            export_filename=experiment_config.export_filename,
        )

        # Update status to completed
        experiment_tracker[experiment_name].status = "completed"
        experiment_tracker[experiment_name].completed_at = datetime.now(UTC)
        logger.info(f"Experiment completed: {experiment_name}")

    except Exception as e:
        # Update status to failed
        experiment_tracker[experiment_name].status = "failed"
        experiment_tracker[experiment_name].completed_at = datetime.now(UTC)
        experiment_tracker[experiment_name].error = str(e)
        logger.error(f"Experiment failed: {experiment_name} - {e}")


@app.get("/api/datasets", response_model=list[DatasetInfo])
async def list_datasets():
    """List available demo datasets.

    Scans the data directory for folders containing both 'businesses/' and 'customers/'
    subdirectories, which indicates a valid dataset.

    Returns:
        List of available datasets with metadata

    """
    data_dir = get_data_directory()

    if not data_dir.exists():
        raise HTTPException(
            status_code=404, detail=f"Data directory not found: {data_dir}"
        )

    datasets = []

    # Scan all subdirectories
    for item in data_dir.iterdir():
        if not item.is_dir():
            continue

        # Skip special directories
        if item.name.startswith(".") or item.name == "data_generation_scripts":
            continue

        businesses_dir = item / "businesses"
        customers_dir = item / "customers"

        # Check if both required directories exist
        if businesses_dir.exists() and customers_dir.exists():
            # Count YAML files in each directory
            num_businesses = len(list(businesses_dir.glob("*.yaml"))) + len(
                list(businesses_dir.glob("*.yml"))
            )
            num_customers = len(list(customers_dir.glob("*.yaml"))) + len(
                list(customers_dir.glob("*.yml"))
            )

            datasets.append(
                DatasetInfo(
                    name=item.name,
                    path=str(item),
                    num_businesses=num_businesses,
                    num_customers=num_customers,
                )
            )

    # Sort by name
    datasets.sort(key=lambda x: x.name)

    return datasets


@app.get("/api/settings", response_model=SettingsResponse)
async def get_settings():
    """Return current default settings and available models.

    Returns system defaults and configuration options that can be used
    when creating new experiments.

    Returns:
        Current system settings and defaults

    """
    return SettingsResponse(
        default_search_algorithm="simple",
        default_search_bandwidth=10,
        default_postgres_host="localhost",
        default_postgres_port=5432,
        available_providers=list(ALLOWED_LLM_PROVIDERS),
    )


@app.post("/api/experiments", response_model=ExperimentStatus)
async def create_experiment(
    experiment_config: ExperimentCreate,
    background_tasks: BackgroundTasks,
):
    """Create and launch a new experiment in the background.

    Accepts configuration for a marketplace experiment and launches it as a
    background task. The experiment will continue running independently and
    its status can be monitored via the status endpoint.

    Args:
        experiment_config: Configuration for the experiment
        background_tasks: FastAPI background tasks manager

    Returns:
        Initial experiment status

    Raises:
        HTTPException: If dataset is invalid or experiment name already exists

    """
    # Validate dataset
    data_dir = get_data_directory()
    dataset_path = Path(experiment_config.dataset)

    # If dataset is not an absolute path, treat it as a name in the data directory
    if not dataset_path.is_absolute():
        dataset_path = data_dir / experiment_config.dataset

    if not dataset_path.exists():
        raise HTTPException(
            status_code=400, detail=f"Dataset not found: {experiment_config.dataset}"
        )

    businesses_dir = dataset_path / "businesses"
    customers_dir = dataset_path / "customers"

    if not businesses_dir.exists() or not customers_dir.exists():
        raise HTTPException(
            status_code=400,
            detail="Invalid dataset: missing businesses/ or customers/ directories",
        )

    # Generate experiment name if not provided
    if experiment_config.experiment_name:
        experiment_name = experiment_config.experiment_name
    else:
        # Count businesses and customers
        num_businesses = len(list(businesses_dir.glob("*.yaml"))) + len(
            list(businesses_dir.glob("*.yml"))
        )
        num_customers = len(list(customers_dir.glob("*.yaml"))) + len(
            list(customers_dir.glob("*.yml"))
        )
        timestamp = int(datetime.now().timestamp() * 1000)
        experiment_name = f"marketplace_{num_customers}_{num_businesses}_{timestamp}"

    # Check if experiment already exists in tracker
    if experiment_name in experiment_tracker and not experiment_config.override:
        raise HTTPException(
            status_code=400,
            detail=f"Experiment '{experiment_name}' already exists. Use override=true to replace it.",
        )

    # Create initial status
    status = ExperimentStatus(
        name=experiment_name,
        status="pending",
        started_at=None,
        completed_at=None,
        error=None,
    )

    experiment_tracker[experiment_name] = status

    # Update dataset path in config to use resolved path
    experiment_config.dataset = str(dataset_path)

    # Schedule the experiment to run in background
    background_tasks.add_task(
        run_experiment_background, experiment_config, experiment_name
    )

    return status


@app.get("/api/experiments/{name}/status", response_model=ExperimentStatus)
async def get_experiment_status(name: str):
    """Check the progress/status of a specific experiment.

    Returns the current status of an experiment, including whether it's
    pending, running, completed, or failed.

    Args:
        name: The experiment name (schema name)

    Returns:
        Current experiment status

    Raises:
        HTTPException: If experiment not found

    """
    if name not in experiment_tracker:
        raise HTTPException(
            status_code=404, detail=f"Experiment '{name}' not found in tracker"
        )

    return experiment_tracker[name]


@app.get("/api/experiments", response_model=list[ExperimentInfo])
async def list_experiments(
    limit: int | None = None,
    host: str = "localhost",
    port: int = 5432,
    database: str = "marketplace",
    user: str = "postgres",
    password: str = "postgres",
):
    """List previous and running experiments from PostgreSQL.

    Queries the PostgreSQL database to list all experiment schemas with their
    metadata including activity timestamps and record counts.

    Args:
        limit: Maximum number of experiments to return
        host: PostgreSQL host
        port: PostgreSQL port
        database: Database name
        user: Database user
        password: Database password

    Returns:
        List of experiments with metadata

    Raises:
        HTTPException: If database connection fails

    """
    try:
        # Connect to PostgreSQL
        conn = await asyncpg.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
        )

        try:
            # Query for all schemas excluding system schemas
            query = """
            SELECT
                s.schema_name,
                COUNT(DISTINCT t.table_name) as table_count
            FROM information_schema.schemata s
            LEFT JOIN information_schema.tables t
                ON s.schema_name = t.table_schema
            WHERE s.schema_name NOT IN ('pg_catalog', 'information_schema', 'public', 'pg_toast')
                AND s.schema_name NOT LIKE 'pg_temp%'
                AND s.schema_name NOT LIKE 'pg_toast%'
            GROUP BY s.schema_name
            ORDER BY s.schema_name
            """

            rows = await conn.fetch(query)

            # For each schema, get the activity information
            experiments = []
            for row in rows:
                schema_name = row["schema_name"]

                # Check if the schema has the required tables
                has_agents = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = $1 AND table_name = 'agents'
                    )
                    """,
                    schema_name,
                )
                has_actions = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = $1 AND table_name = 'actions'
                    )
                    """,
                    schema_name,
                )
                has_logs = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = $1 AND table_name = 'logs'
                    )
                    """,
                    schema_name,
                )

                # Skip schemas that don't have all three required tables
                if not (has_agents and has_actions and has_logs):
                    continue

                # Get activity timestamps
                first_activity = await conn.fetchval(
                    f"SELECT MIN(created_at) FROM {schema_name}.agents"
                )

                queries = [
                    f"SELECT MAX(created_at) as max_created_at FROM {schema_name}.agents",
                    f"SELECT MAX(created_at) as max_created_at FROM {schema_name}.actions",
                    f"SELECT MAX(created_at) as max_created_at FROM {schema_name}.logs",
                ]
                union_query = " UNION ALL ".join(queries)
                last_activity = await conn.fetchval(
                    f"SELECT MAX(max_created_at) FROM ({union_query}) AS dates"
                )

                # Get row counts
                agents_count = await conn.fetchval(
                    f"SELECT COUNT(*) FROM {schema_name}.agents"
                )
                actions_count = await conn.fetchval(
                    f"SELECT COUNT(*) FROM {schema_name}.actions"
                )
                logs_count = await conn.fetchval(
                    f"SELECT COUNT(*) FROM {schema_name}.logs"
                )

                # Get LLM providers
                llm_providers = []
                try:
                    provider_rows = await conn.fetch(
                        f"""
                        SELECT DISTINCT jsonb_path_query_first(data, '$.data.provider') #>> '{{}}' as provider
                        FROM {schema_name}.logs
                        WHERE jsonb_path_query_first(data, '$.data.provider') IS NOT NULL
                        """
                    )
                    llm_providers = [
                        row["provider"] for row in provider_rows if row["provider"]
                    ]
                except Exception:
                    pass

                experiments.append(
                    ExperimentInfo(
                        schema_name=schema_name,
                        first_activity=first_activity,
                        last_activity=last_activity,
                        agents_count=agents_count or 0,
                        actions_count=actions_count or 0,
                        logs_count=logs_count or 0,
                        llm_providers=llm_providers,
                    )
                )

            # Sort by first activity (most recent first)
            experiments.sort(
                key=lambda x: x.first_activity or datetime.min.replace(tzinfo=UTC),
                reverse=True,
            )

            # Apply limit if specified
            if limit is not None and limit > 0:
                experiments = experiments[:limit]

            return experiments

        finally:
            await conn.close()

    except asyncpg.InvalidCatalogNameError as e:
        raise HTTPException(
            status_code=404, detail=f"Database '{database}' does not exist"
        ) from e
    except asyncpg.InvalidPasswordError as e:
        raise HTTPException(status_code=401, detail="Invalid database password") from e
    except Exception as e:
        logger.error(f"Failed to list experiments: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list experiments: {str(e)}"
        ) from e


@app.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        Simple health status

    """
    return {"status": "healthy"}
