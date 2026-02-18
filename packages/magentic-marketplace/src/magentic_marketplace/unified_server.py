"""Unified FastAPI server for both orchestrator API and visualizer UI.

This module provides a single FastAPI application that serves:
- Orchestrator API for launching and managing experiments (/api/experiments, /api/datasets, etc.)
- Visualizer API for viewing a specific experiment's results (/api/customers, /api/businesses, etc.)
- Static UI files (React SPA) at the root path

The visualizer API connects to a specific experiment schema specified at server startup.
"""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import the existing API app and its routes
from magentic_marketplace.api import main as orchestrator_api

# Import visualizer utilities
from magentic_marketplace.ui.server import (
    _create_message_threads,
    _load_businesses,
    _load_customers,
    _load_messages,
)
from magentic_marketplace.experiments.run_analytics import MarketplaceAnalytics
from magentic_marketplace.platform.database import connect_to_postgresql_database

logger = logging.getLogger(__name__)


def create_unified_app(
    visualizer_schema: str | None = None,
    postgres_host: str = "localhost",
    postgres_port: int = 5432,
    postgres_password: str = "postgres",
) -> FastAPI:
    """Create unified FastAPI app combining orchestrator and visualizer.

    Args:
        visualizer_schema: PostgreSQL schema name for visualizer (optional)
        postgres_host: PostgreSQL host for visualizer connections
        postgres_port: PostgreSQL port for visualizer connections
        postgres_password: PostgreSQL password for visualizer connections

    Returns:
        Configured unified FastAPI application

    """
    # Create a new FastAPI app
    app = FastAPI(
        title="Magentic Marketplace Unified Server",
        description="Unified API for experiment orchestration and visualization",
        version="1.0.0",
    )

    # Enable CORS for frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include orchestrator routes from the orchestrator app
    # We copy the routes instead of mounting to avoid path prefix issues
    for route in orchestrator_api.app.routes:
        app.router.routes.append(route)

    # Add visualizer API routes if schema is provided
    if visualizer_schema:
        logger.info(f"Adding visualizer routes for schema: {visualizer_schema}")

        @app.on_event("startup")
        async def startup_visualizer():
            """Connect to visualizer database on startup."""
            global _db_controller
            logger.info("Connecting to PostgreSQL for visualizer...")
            logger.info(f"Host: {postgres_host}:{postgres_port}")
            logger.info(f"Schema: {visualizer_schema}")

            # Create database connection (managed by context manager in lifespan)
            # For now, we'll connect in each endpoint
            pass

        @app.get("/api/customers")
        async def get_visualizer_customers():
            """Get all customers for the configured experiment schema."""
            try:
                async with connect_to_postgresql_database(
                    schema=visualizer_schema,
                    host=postgres_host,
                    port=postgres_port,
                    password=postgres_password,
                    mode="existing",
                ) as db:
                    # Set the global db controller for the ui.server module functions
                    import magentic_marketplace.ui.server as ui_server

                    ui_server._db_controller = db
                    customers = await _load_customers()
                    ui_server._db_controller = None
                    return customers
            except Exception as e:
                logger.error(f"Error loading customers: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Unable to load customers: {str(e)}"
                )

        @app.get("/api/businesses")
        async def get_visualizer_businesses():
            """Get all businesses for the configured experiment schema."""
            try:
                async with connect_to_postgresql_database(
                    schema=visualizer_schema,
                    host=postgres_host,
                    port=postgres_port,
                    password=postgres_password,
                    mode="existing",
                ) as db:
                    # Set the global db controller for the ui.server module functions
                    import magentic_marketplace.ui.server as ui_server

                    ui_server._db_controller = db
                    businesses = await _load_businesses()
                    ui_server._db_controller = None
                    return businesses
            except Exception as e:
                logger.error(f"Error loading businesses: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Unable to load businesses: {str(e)}"
                )

        @app.get("/api/marketplace-data")
        async def get_visualizer_marketplace_data():
            """Get messages, threads, and analytics for the configured experiment schema."""
            try:
                async with connect_to_postgresql_database(
                    schema=visualizer_schema,
                    host=postgres_host,
                    port=postgres_port,
                    password=postgres_password,
                    mode="existing",
                ) as db:
                    # Set the global db controller for the ui.server module functions
                    import magentic_marketplace.ui.server as ui_server

                    ui_server._db_controller = db

                    customers = await _load_customers()
                    businesses = await _load_businesses()
                    messages = await _load_messages()
                    threads_dict, threads_with_payments = _create_message_threads(
                        customers, businesses, messages
                    )

                    # Calculate analytics
                    analytics = MarketplaceAnalytics(db)
                    await analytics.load_data()
                    await analytics.analyze_actions()
                    analytics_results = analytics.collect_analytics_results()

                    for thread_key in threads_with_payments:
                        thread = threads_dict[thread_key]
                        customer_id = thread["participants"]["customer"]["id"]
                        business_id = thread["participants"]["business"]["id"]

                        # Calculate utility for this specific conversation
                        conversation_utility = (
                            analytics.calculate_conversation_utility(
                                customer_id, business_id
                            )
                        )
                        thread["utility"] = conversation_utility

                    # Convert to list and sort by lastMessageTime
                    message_threads = list(threads_dict.values())
                    message_threads.sort(
                        key=lambda x: x["lastMessageTime"], reverse=True
                    )

                    # Build customer analytics dict
                    customer_analytics = {}
                    for customer_summary in analytics_results.customer_summaries:
                        customer_analytics[customer_summary.customer_id] = {
                            "utility": customer_summary.utility,
                            "payments_made": customer_summary.payments_made,
                            "proposals_received": customer_summary.proposals_received,
                        }

                    # Build business analytics dict
                    business_analytics = {}
                    for business_summary in analytics_results.business_summaries:
                        # Count payments received for this business
                        payments_received = 0
                        for customer_payments in analytics.customer_payments.values():
                            for payment in customer_payments:
                                business_id = analytics._find_business_for_proposal(
                                    payment.proposal_message_id
                                )
                                if business_id == business_summary.business_id:
                                    payments_received += 1

                        business_analytics[business_summary.business_id] = {
                            "utility": business_summary.utility,
                            "proposals_sent": business_summary.proposals_sent,
                            "payments_received": payments_received,
                        }

                    # Marketplace summary
                    marketplace_summary = {
                        "total_utility": analytics_results.total_marketplace_customer_utility,
                        "total_payments": analytics_results.transaction_summary.payments_made,
                        "total_proposals": analytics_results.transaction_summary.order_proposals_created,
                    }

                    ui_server._db_controller = None

                    return {
                        "messages": messages,
                        "messageThreads": message_threads,
                        "analytics": {
                            "customer_analytics": customer_analytics,
                            "business_analytics": business_analytics,
                            "marketplace_summary": marketplace_summary,
                        },
                    }
            except Exception as e:
                logger.error(f"Error loading marketplace data: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Unable to load marketplace data: {str(e)}"
                )

    # Mount static files at root (for UI) - must be last
    static_dir = Path(__file__).parent / "ui" / "static"
    if static_dir.exists():
        logger.info(f"Mounting static files from: {static_dir}")
        app.mount(
            "/", StaticFiles(directory=str(static_dir), html=True), name="static"
        )
    else:
        logger.warning(f"Static directory not found: {static_dir}")

    return app


def run_unified_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    visualizer_schema: str | None = None,
    postgres_host: str = "localhost",
    postgres_port: int = 5432,
    postgres_password: str = "postgres",
    log_level: str = "info",
):
    """Run the unified server.

    Args:
        host: Server host
        port: Server port
        visualizer_schema: PostgreSQL schema name for visualizer (optional)
        postgres_host: PostgreSQL host for visualizer connections
        postgres_port: PostgreSQL port for visualizer connections
        postgres_password: PostgreSQL password for visualizer connections
        log_level: Logging level

    """
    import uvicorn

    print("Starting Magentic Marketplace Unified Server...", flush=True)
    print(f"Server will be available at: http://{host}:{port}", flush=True)
    print(f"Orchestrator API: http://{host}:{port}/api/experiments", flush=True)
    if visualizer_schema:
        print(
            f"Visualizer API: http://{host}:{port}/api/customers (schema: {visualizer_schema})",
            flush=True,
        )
        print(f"UI: http://{host}:{port}/", flush=True)
    else:
        print("Visualizer: Not configured (no schema specified)", flush=True)

    app = create_unified_app(
        visualizer_schema=visualizer_schema,
        postgres_host=postgres_host,
        postgres_port=postgres_port,
        postgres_password=postgres_password,
    )

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level.lower(),
    )
