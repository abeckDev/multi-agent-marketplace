# API Server

The Magentic Marketplace includes a REST API server for launching and managing marketplace experiments programmatically.

## Starting the API Server

Launch the API server using the `api` command:

```bash
magentic-marketplace api
```

By default, the API server starts on `localhost:8000`. You can customize the host and port:

```bash
magentic-marketplace api --api-host 0.0.0.0 --api-port 8080
```

## API Documentation

Once the server is running, you can access the interactive API documentation:

- **Swagger UI**: Navigate to `http://localhost:8000/docs` in your browser
- **ReDoc**: Navigate to `http://localhost:8000/redoc` for alternative documentation
- **OpenAPI JSON**: Access the raw OpenAPI schema at `http://localhost:8000/openapi.json`

## Available Endpoints

### Datasets

- `GET /api/datasets` - List all available demo datasets

### Settings

- `GET /api/settings` - Get system configuration and available LLM providers

### Experiments

- `POST /api/experiments` - Create and launch a new experiment
- `GET /api/experiments` - List all experiments from the database
- `GET /api/experiments/{name}/status` - Check the status of a specific experiment

### Health

- `GET /health` - Health check endpoint for monitoring

## Example Usage

### List Available Datasets

```bash
curl http://localhost:8000/api/datasets
```

### Create a New Experiment

```bash
curl -X POST http://localhost:8000/api/experiments \
  -H "Content-Type: application/json" \
  -d '{
    "dataset": "demo_small",
    "experiment_name": "my_first_experiment",
    "search_algorithm": "simple",
    "search_bandwidth": 10,
    "postgres_host": "localhost",
    "postgres_port": 5432,
    "postgres_password": "postgres"
  }'
```

### Check Experiment Status

```bash
curl http://localhost:8000/api/experiments/my_first_experiment/status
```

## Features

- **Background Processing**: Experiments run asynchronously, allowing you to launch multiple experiments
- **Real-time Status**: Monitor experiment progress through status endpoints
- **Database Integration**: All experiment data is stored in PostgreSQL
- **Interactive Documentation**: Swagger UI provides a user-friendly interface to explore and test all endpoints

## Requirements

Before using the API, ensure you have:

1. PostgreSQL running and accessible (default: `localhost:5432`)
2. Required environment variables set (see [Environment Variables](/usage/env))
3. At least one dataset available in the `data/` directory

## Command Options

- `--api-host`: Host address for the API server (default: `127.0.0.1`)
- `--api-port`: Port number for the API server (default: `8000`)
- `--log-level`: Logging level (default: `info`)

Run `magentic-marketplace api --help` for all available options.
