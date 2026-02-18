"""Unified FastAPI server for both orchestrator API and visualizer UI.

This module provides a single FastAPI application that serves:
- Orchestrator API for launching and managing experiments (/api/experiments, /api/datasets, etc.)
- Visualizer API for viewing experiment results (/api/visualizer/{schema}/*)
- Static UI files (React SPA) at the root path
"""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import the existing API app and its routes
from magentic_marketplace.api import main as orchestrator_api

# Import visualizer utilities
from magentic_marketplace.experiments.run_analytics import MarketplaceAnalytics
from magentic_marketplace.marketplace.actions import ActionAdapter, Search, SendMessage
from magentic_marketplace.marketplace.shared.models import (
    BusinessAgentProfile,
    CustomerAgentProfile,
    MarketplaceAgentProfileAdapter,
)
from magentic_marketplace.platform.database import (
    connect_to_postgresql_database,
    connect_to_sqlite_database,
)
from magentic_marketplace.platform.database.base import BaseDatabaseController

logger = logging.getLogger(__name__)


def create_unified_app(
    postgres_host: str = "localhost",
    postgres_port: int = 5432,
    postgres_password: str = "postgres",
) -> FastAPI:
    """Create unified FastAPI app combining orchestrator and visualizer.

    Args:
        postgres_host: PostgreSQL host for visualizer connections
        postgres_port: PostgreSQL port for visualizer connections
        postgres_password: PostgreSQL password for visualizer connections

    Returns:
        Configured unified FastAPI application

    """
    # Use the orchestrator app as the base and add visualizer routes to it
    app = orchestrator_api.app
    
    # Update app metadata
    app.title = "Magentic Marketplace Unified Server"
    app.description = "Unified API for experiment orchestration and visualization"

    # Enable CORS for frontend access (if not already added)
    # Check if CORS middleware already exists
    has_cors = any(
        isinstance(middleware, CORSMiddleware) 
        for middleware in getattr(app, 'user_middleware', [])
    )
    if not has_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Visualizer API routes for a specific experiment
    # These will be at /api/visualizer/{schema}/*
    @app.get("/api/visualizer/{schema}/customers")
    async def get_visualizer_customers(schema: str):
        """Get all customers for a specific experiment schema."""
        try:
            async with connect_to_postgresql_database(
                schema=schema,
                host=postgres_host,
                port=postgres_port,
                password=postgres_password,
                mode="existing",
            ) as db:
                customers = await _load_customers(db)
                return customers
        except Exception as e:
            logger.error(f"Error loading customers for schema {schema}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Unable to load customers: {str(e)}"
            )

    @app.get("/api/visualizer/{schema}/businesses")
    async def get_visualizer_businesses(schema: str):
        """Get all businesses for a specific experiment schema."""
        try:
            async with connect_to_postgresql_database(
                schema=schema,
                host=postgres_host,
                port=postgres_port,
                password=postgres_password,
                mode="existing",
            ) as db:
                businesses = await _load_businesses(db)
                return businesses
        except Exception as e:
            logger.error(f"Error loading businesses for schema {schema}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Unable to load businesses: {str(e)}"
            )

    @app.get("/api/visualizer/{schema}/marketplace-data")
    async def get_visualizer_marketplace_data(schema: str):
        """Get messages, threads, and analytics for a specific experiment schema."""
        try:
            async with connect_to_postgresql_database(
                schema=schema,
                host=postgres_host,
                port=postgres_port,
                password=postgres_password,
                mode="existing",
            ) as db:
                customers = await _load_customers(db)
                businesses = await _load_businesses(db)
                messages = await _load_messages(db)
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
                    conversation_utility = analytics.calculate_conversation_utility(
                        customer_id, business_id
                    )
                    thread["utility"] = conversation_utility

                # Convert to list and sort by lastMessageTime
                message_threads = list(threads_dict.values())
                message_threads.sort(key=lambda x: x["lastMessageTime"], reverse=True)

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
            logger.error(f"Error loading marketplace data for schema {schema}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Unable to load marketplace data: {str(e)}"
            )

    @app.get("/api/visualizer/health")
    def visualizer_health_check():
        """Health check endpoint for visualizer API."""
        return {
            "status": "healthy",
            "service": "visualizer",
        }

    # Mount static files at root (for UI) - must be last
    static_dir = Path(__file__).parent / "ui" / "static"
    if static_dir.exists():
        app.mount(
            "/", StaticFiles(directory=str(static_dir), html=True), name="static"
        )
    else:
        logger.warning(f"Static directory not found: {static_dir}")

    return app


async def _load_customers(db: BaseDatabaseController):
    """Load all customer agents from the database.

    Args:
        db: Database controller instance

    Returns:
        List of customer data dictionaries

    """
    agent_rows = await db.agents.get_all()
    customers = []

    for agent_row in agent_rows:
        agent = MarketplaceAgentProfileAdapter.validate_python(
            agent_row.data.model_dump()
        )

        if isinstance(agent, CustomerAgentProfile):
            customer_data = agent.customer
            customer = {
                "id": agent.id,
                "name": customer_data.name,
                "user_request": customer_data.request,
                "menu_features": customer_data.menu_features,
                "amenity_features": customer_data.amenity_features,
            }
            customers.append(customer)

    return customers


async def _load_businesses(db: BaseDatabaseController):
    """Load all business agents from the database.

    Args:
        db: Database controller instance

    Returns:
        List of business data dictionaries

    """
    agent_rows = await db.agents.get_all()
    businesses = []

    for agent_row in agent_rows:
        agent = MarketplaceAgentProfileAdapter.validate_python(
            agent_row.data.model_dump()
        )

        if isinstance(agent, BusinessAgentProfile):
            business_data = agent.business
            business = {
                "id": agent.id,
                "name": business_data.name,
                "rating": business_data.rating,
                "price_min": min(business_data.menu_features.values())
                if business_data.menu_features
                else 0,
                "price_max": max(business_data.menu_features.values())
                if business_data.menu_features
                else 0,
                "description": business_data.description,
                "menu_features": business_data.menu_features,
                "amenity_features": business_data.amenity_features,
            }
            businesses.append(business)

    return businesses


async def _load_messages(db: BaseDatabaseController):
    """Load all messages from actions in the database.

    Args:
        db: Database controller instance

    Returns:
        List of message data dictionaries

    """
    action_rows = await db.actions.get_all()
    messages = []

    for action_row in action_rows:
        action_request = action_row.data.request
        action_result = action_row.data.result

        if action_result.is_error:
            continue

        try:
            action = ActionAdapter.validate_python(action_request.parameters)

            if isinstance(action, SendMessage):
                message_content = action.message
                content_dict = message_content.model_dump(mode="json")

                if message_content.type == "text" and "content" in content_dict:
                    content_value = content_dict["content"]
                else:
                    content_value = content_dict

                message = {
                    "id": action_row.id,
                    "to_agent": action.to_agent_id,
                    "from_agent": action.from_agent_id,
                    "type": message_content.type,
                    "content": content_value,
                    "created_at": action.created_at.isoformat(),
                }
                messages.append(message)
            elif isinstance(action, Search):
                # Extract business IDs from search results
                result_content = action_result.content
                business_ids = []
                if result_content and "businesses" in result_content:
                    business_ids = [
                        b.get("id") for b in result_content["businesses"] if "id" in b
                    ]

                # Create search result message
                search_content = {
                    "type": "search",
                    "query": action.query,
                    "business_ids": business_ids,
                    "total_results": len(business_ids),
                }

                message = {
                    "id": action_row.id,
                    "from_agent": action_row.data.agent_id,
                    "to_agent": None,  # Search doesn't have a specific recipient
                    "type": "search",
                    "content": search_content,
                    "created_at": action_row.created_at.isoformat(),
                    "business_ids": business_ids,  # Store for thread matching
                }
                messages.append(message)
        except Exception as e:
            logger.warning(f"Failed to parse action {action_row.id}: {e}")
            continue

    return messages


def _create_message_threads(customers, businesses, messages):
    """Create message threads from customers, businesses, and messages.

    Args:
        customers: List of customer data
        businesses: List of business data
        messages: List of message data

    Returns:
        tuple: (threads_dict, threads_with_payments_set) where:
            - threads_dict: dict of thread_key -> thread data
            - threads_with_payments_set: set of thread_keys that have payments

    """
    threads = {}
    threads_with_payments = set()
    customer_by_agent_id = {c["id"]: c for c in customers}
    business_by_agent_id = {b["id"]: b for b in businesses}

    for message in messages:
        from_agent = message["from_agent"]
        to_agent = message.get("to_agent")

        # Handle search messages specially - they create threads with all matched businesses
        if message["type"] == "search" and "business_ids" in message:
            customer = customer_by_agent_id.get(from_agent)
            if customer:
                for business_id in message["business_ids"]:
                    business = business_by_agent_id.get(business_id)
                    if business:
                        thread_key = f"{customer['id']}-{business_id}"

                        if thread_key not in threads:
                            threads[thread_key] = {
                                "participants": {
                                    "customer": customer,
                                    "business": business,
                                },
                                "messages": [],
                                "lastMessageTime": message["created_at"],
                                "utility": 0,  # Default utility
                            }

                        # Add search message to each relevant thread
                        thread_message = message.copy()
                        thread_message.pop(
                            "business_ids", None
                        )  # Remove internal field
                        threads[thread_key]["messages"].append(thread_message)
                        threads[thread_key]["lastMessageTime"] = message["created_at"]
        else:
            # Handle regular messages (SendMessage)
            customer = customer_by_agent_id.get(from_agent) or customer_by_agent_id.get(
                to_agent
            )
            business = business_by_agent_id.get(from_agent) or business_by_agent_id.get(
                to_agent
            )

            if customer and business:
                customer_id = customer["id"]
                business_id = business["id"]
                thread_key = f"{customer_id}-{business_id}"

                if thread_key not in threads:
                    threads[thread_key] = {
                        "participants": {"customer": customer, "business": business},
                        "messages": [],
                        "lastMessageTime": message["created_at"],
                        "utility": 0,  # Default utility
                    }

                threads[thread_key]["messages"].append(message)
                threads[thread_key]["lastMessageTime"] = message["created_at"]

                # Track threads with payments (customer sending payment to business)
                if message["type"] == "payment" and from_agent == customer_id:
                    threads_with_payments.add(thread_key)

    return threads, threads_with_payments


def run_unified_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    postgres_host: str = "localhost",
    postgres_port: int = 5432,
    postgres_password: str = "postgres",
    log_level: str = "info",
):
    """Run the unified server.

    Args:
        host: Server host
        port: Server port
        postgres_host: PostgreSQL host for visualizer connections
        postgres_port: PostgreSQL port for visualizer connections
        postgres_password: PostgreSQL password for visualizer connections
        log_level: Logging level

    """
    import uvicorn

    print("Starting Magentic Marketplace Unified Server...", flush=True)
    print(f"Server will be available at: http://{host}:{port}", flush=True)
    print(f"Orchestrator API: http://{host}:{port}/api/experiments", flush=True)
    print(f"Visualizer API: http://{host}:{port}/api/visualizer/{{schema}}/...", flush=True)
    print(f"UI: http://{host}:{port}/", flush=True)

    app = create_unified_app(
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
