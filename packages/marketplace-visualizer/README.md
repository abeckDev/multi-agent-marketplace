# Marketplace Visualizer

Visualize and manage marketplace experiments!

## Features

- **Experiment Dashboard** - Launch and monitor experiments from a web interface
- **Experiment Visualizer** - View detailed results of completed experiments
- **Orchestrator API Integration** - Launch experiments via REST API
- **Real-time Status Polling** - Track experiment progress in real-time

## Quick Start

### Option 1: Using the Unified Server (Recommended)

The unified server provides both the orchestrator API and the visualizer UI:

```bash
cd multi-agent-marketplace
docker compose up -d

# Start the unified server
magentic-marketplace serve --host 0.0.0.0 --port 8000
```

Then open your browser to:
- **Dashboard**: http://localhost:8000/dashboard - Launch and manage experiments
- **API Docs**: http://localhost:8000/docs - View API documentation
- **Visualizer**: http://localhost:8000/ - View experiment results (requires running experiment)

### Option 2: Running Experiments via CLI

First, run an experiment to get a schema name:

```bash
cd multi-agent-marketplace
docker compose up -d

magentic-marketplace run data/mexican_3_9 --experiment-name myexperiment123
```

Then you can launch the visualizer:

```bash
magentic-marketplace ui myexperiment123
```

## Dashboard Features

The experiment launcher dashboard (`/dashboard`) provides:

- **Dataset Selection** - Choose from available datasets in the `data/` directory
- **Experiment Configuration** - Set parameters like search algorithm, bandwidth, and customer max steps
- **PostgreSQL Settings** - Configure database connection for experiments
- **Real-time Monitoring** - See running experiments with live status updates
- **Experiment History** - View all completed experiments with metadata
- **Quick Navigation** - Click "View" to open any experiment in the visualizer

## Architecture

```
Browser → Dashboard (React) → Orchestrator API → Experiment Runner → PostgreSQL
                            ↓
                     Visualizer (React) → Visualizer API → PostgreSQL
```

## Dev

To make changes you first need to install the frontend code then run the server in dev mode

```bash
cd marketplace-visualizer
uv sync
npm install
npm run build # builds output files
```

Then launch UI in dev mode

```bash
cd marketplace-visualizer
npm run dev
```

And also launch a backend server:

```bash
magentic-marketplace serve
```

The Vite dev server will proxy API calls to the backend server (default: http://localhost:8000).

## Routing

The application uses React Router with the following routes:

- `/dashboard` - Experiment launcher dashboard
- `/` - Experiment visualizer (requires schema parameter or configured backend)

Navigation between the dashboard and visualizer is seamless with "Back to Dashboard" links.
