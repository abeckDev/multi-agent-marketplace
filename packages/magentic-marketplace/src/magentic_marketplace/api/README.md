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

### `GET /api/experiments/{name}/logs`

Get recent logs for a specific experiment (REST fallback for clients that cannot use WebSockets).

**Query Parameters:**
- `since` (optional): Get logs after this timestamp (ISO 8601 format)
- `limit` (optional): Maximum number of logs to return (1-1000, default: 100)
- `host` (optional): PostgreSQL host (default: localhost)
- `port` (optional): PostgreSQL port (default: 5432)
- `database` (optional): Database name (default: marketplace)
- `user` (optional): Database user (default: postgres)
- `password` (optional): Database password (default: postgres)

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2024-02-18T04:32:00Z",
      "level": "info",
      "message": "Customer agent registered",
      "data": {"customer_id": "customer_001"},
      "agent_id": "customer_001"
    }
  ],
  "total": 150,
  "has_more": true
}
```

**Example:**
```bash
# Get latest 50 logs
curl "http://localhost:8000/api/experiments/my_experiment/logs?limit=50"

# Get logs since a specific time
curl "http://localhost:8000/api/experiments/my_experiment/logs?since=2024-02-18T04:32:00Z"
```

### `WS /api/experiments/{name}/logs/ws`

Stream live logs for a running experiment via WebSocket. Provides real-time log updates.

**Query Parameters:**
- `since` (optional): Start streaming from this timestamp (ISO 8601 format)
- `host` (optional): PostgreSQL host (default: localhost)
- `port` (optional): PostgreSQL port (default: 5432)
- `database` (optional): Database name (default: marketplace)
- `user` (optional): Database user (default: postgres)
- `password` (optional): Database password (default: postgres)

**WebSocket Message Format:**

Messages sent from server to client:

```json
{
  "type": "log",
  "log": {
    "timestamp": "2024-02-18T04:32:00Z",
    "level": "info",
    "message": "Customer agent registered",
    "data": {"customer_id": "customer_001"},
    "agent_id": "customer_001"
  }
}
```

```json
{
  "type": "status",
  "status": "completed"
}
```

```json
{
  "type": "error",
  "error": "Connection error message"
}
```

**Message Types:**
- `log`: Contains a single log entry in the `log` field
- `status`: Sent when experiment status changes (completed/failed), contains status in `status` field
- `error`: Sent when an error occurs, contains error message in `error` field

**WebSocket Client Example (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/experiments/my_experiment/logs/ws');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  if (message.type === 'log') {
    console.log(`[${message.log.level}] ${message.log.message}`);
  } else if (message.type === 'status') {
    console.log(`Experiment ${message.status}`);
    ws.close();
  } else if (message.type === 'error') {
    console.error(`Error: ${message.error}`);
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

**WebSocket Client Example (Python):**
```python
import asyncio
import websockets
import json

async def stream_logs(experiment_name):
    uri = f"ws://localhost:8000/api/experiments/{experiment_name}/logs/ws"
    
    async with websockets.connect(uri) as websocket:
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                
                if data['type'] == 'log':
                    log = data['log']
                    print(f"[{log['level']}] {log['message']}")
                elif data['type'] == 'status':
                    print(f"Experiment {data['status']}")
                    break
                elif data['type'] == 'error':
                    print(f"Error: {data['error']}")
                    break
            except websockets.exceptions.ConnectionClosed:
                break

# Run the stream
asyncio.run(stream_logs('my_experiment'))
```

**Behavior:**
- The WebSocket connection streams logs in real-time as they are generated
- Logs are polled from the database every 500ms
- When the experiment completes or fails, a final status message is sent and the connection closes
- If the client disconnects, resources are cleaned up automatically
- Schema/experiment names are validated to prevent SQL injection

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
- **WebSocket Support**: Real-time log streaming for running experiments

## Security

### Schema Name Validation

All experiment/schema names are validated to prevent SQL injection attacks:

- **Allowed**: Alphanumeric characters (a-z, A-Z, 0-9) and underscores (_)
- **Must not start with**: A digit
- **Blocked**: Special characters like `;`, `-`, `.`, `'`, `"`, `/`, `\`, `$`, etc.

Examples:
- ✅ `my_experiment_123`
- ✅ `marketplace_10_5_1234567890`
- ❌ `test-experiment` (hyphen not allowed)
- ❌ `test;DROP TABLE` (SQL injection attempt)
- ❌ `123experiment` (cannot start with digit)

This validation applies to:
- `GET /api/experiments/{name}/logs`
- `WS /api/experiments/{name}/logs/ws`
- `GET /api/experiments/{name}/status`

Invalid names return a 400 Bad Request error with a clear error message.

## Notes

- Experiments run in the background and continue independently after API response
- Status tracking is in-memory (resets on API server restart)
- PostgreSQL database required for listing historical experiments
- All dataset paths are validated before launching experiments
- Error messages include detailed information for debugging
