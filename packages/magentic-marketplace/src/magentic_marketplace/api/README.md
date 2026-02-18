# Marketplace Orchestrator API

FastAPI-based REST API for launching and managing marketplace experiments programmatically.

## Features

- **Dataset Management**: List available datasets with metadata
- **Experiment Orchestration**: Launch experiments in background with full configuration control
- **Status Tracking**: Monitor experiment progress (pending, running, completed, failed)
- **PostgreSQL Integration**: List and query historical experiments
- **OpenAPI Documentation**: Auto-generated API docs at `/docs`

## Quick Start

### Start the API Server

```bash
# Default: http://0.0.0.0:8000
magentic-marketplace api

# Custom host and port
magentic-marketplace api --api-host localhost --api-port 8765

# With debug logging
magentic-marketplace api --log-level DEBUG
```

### Access API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI Schema: http://localhost:8000/openapi.json

## API Endpoints

### `GET /api/datasets`

List all available datasets.

**Response:**
```json
[
  {
    "name": "mexican_3_9",
    "path": "/path/to/data/mexican_3_9",
    "num_businesses": 9,
    "num_customers": 3
  }
]
```

### `GET /api/settings`

Get current system defaults and configuration options.

**Response:**
```json
{
  "default_search_algorithm": "simple",
  "default_search_bandwidth": 10,
  "default_postgres_host": "localhost",
  "default_postgres_port": 5432,
  "available_providers": ["openai", "gemini", "anthropic", "azure_openai"]
}
```

### `POST /api/experiments`

Create and launch a new experiment in background.

**Request Body:**
```json
{
  "dataset": "mexican_3_9",
  "experiment_name": "my_experiment",
  "search_algorithm": "simple",
  "search_bandwidth": 10,
  "customer_max_steps": null,
  "postgres_host": "localhost",
  "postgres_port": 5432,
  "postgres_password": "postgres",
  "override": false,
  "export_sqlite": false
}
```

**Response:**
```json
{
  "name": "my_experiment",
  "status": "pending",
  "started_at": null,
  "completed_at": null,
  "error": null
}
```

### `GET /api/experiments/{name}/status`

Check the status of a specific experiment.

**Response:**
```json
{
  "name": "my_experiment",
  "status": "running",
  "started_at": "2024-02-18T04:32:00Z",
  "completed_at": null,
  "error": null
}
```

Status values: `pending`, `running`, `completed`, `failed`

### `GET /api/experiments`

List all experiments stored in PostgreSQL.

**Query Parameters:**
- `limit` (optional): Maximum number of experiments to return
- `host` (optional): PostgreSQL host (default: localhost)
- `port` (optional): PostgreSQL port (default: 5432)
- `database` (optional): Database name (default: marketplace)
- `user` (optional): Database user (default: postgres)
- `password` (optional): Database password (default: postgres)

**Response:**
```json
[
  {
    "schema_name": "marketplace_3_9_1234567890",
    "first_activity": "2024-02-18T04:32:00Z",
    "last_activity": "2024-02-18T04:35:00Z",
    "agents_count": 12,
    "actions_count": 45,
    "logs_count": 120,
    "llm_providers": ["openai"]
  }
]
```

### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

## Usage Examples

### cURL

```bash
# List datasets
curl http://localhost:8000/api/datasets

# Create experiment
curl -X POST http://localhost:8000/api/experiments \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "mexican_3_9",
    "experiment_name": "test_experiment"
  }'

# Check experiment status
curl http://localhost:8000/api/experiments/test_experiment/status

# List all experiments
curl http://localhost:8000/api/experiments
```

### Python

```python
import requests

# Base URL
base_url = "http://localhost:8000"

# List datasets
response = requests.get(f"{base_url}/api/datasets")
datasets = response.json()

# Create experiment
experiment_config = {
    "dataset": "mexican_3_9",
    "experiment_name": "my_experiment",
    "search_bandwidth": 20
}
response = requests.post(f"{base_url}/api/experiments", json=experiment_config)
status = response.json()

# Poll for completion
import time
while True:
    response = requests.get(f"{base_url}/api/experiments/{status['name']}/status")
    current_status = response.json()
    if current_status['status'] in ['completed', 'failed']:
        break
    time.sleep(10)
```

## Integration with Existing CLI

The API is fully compatible with the existing CLI. All CLI operations remain unchanged:

```bash
# CLI still works as before
magentic-marketplace run data/mexican_3_9

# API provides additional programmatic access
magentic-marketplace api
```

## Configuration Options

When creating experiments via `POST /api/experiments`, all CLI options are supported:

- `dataset`: Dataset name or absolute path (required)
- `experiment_name`: Custom name (auto-generated if not provided)
- `search_algorithm`: Customer search strategy (default: "simple")
- `search_bandwidth`: Search result limits (default: 10)
- `customer_max_steps`: Max agent steps before stopping
- `postgres_host`: PostgreSQL host (default: "localhost")
- `postgres_port`: PostgreSQL port (default: 5432)
- `postgres_password`: PostgreSQL password (default: "postgres")
- `db_pool_min_size`: Connection pool min size (default: 2)
- `db_pool_max_size`: Connection pool max size (default: 10)
- `server_host`: Server host (default: "127.0.0.1")
- `server_port`: Server port (default: 0 for auto-assign)
- `override`: Override existing experiment (default: false)
- `export_sqlite`: Export results to SQLite (default: false)
- `export_dir`: Directory for SQLite export
- `export_filename`: Filename for SQLite export

## Architecture

- **FastAPI Application**: Modern async web framework
- **Background Tasks**: Experiments run independently without blocking
- **In-Memory Tracking**: Lightweight status tracking for running experiments
- **PostgreSQL Integration**: Query historical experiment data
- **OpenAPI Support**: Auto-generated documentation and client libraries

## Notes

- Experiments run in the background and continue independently after API response
- Status tracking is in-memory (resets on API server restart)
- PostgreSQL database required for listing historical experiments
- All dataset paths are validated before launching experiments
- Error messages include detailed information for debugging
