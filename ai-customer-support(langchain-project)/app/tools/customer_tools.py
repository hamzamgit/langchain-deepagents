"""Customer-related tools."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app.middleware.logging import log_tool_call
from app.services import customer_service
from app.tools._session import with_session


@tool
async def get_customer(customer_id: str) -> dict[str, Any]:
    """Get customer profile by ID. Never invent customer data."""

    async def _run(session):
        with log_tool_call(conversation_id=None, agent="shared", tool="get_customer"):
            customer = await customer_service.get_customer(session, customer_id)
            if customer is None:
                return {"error": f"Customer {customer_id} not found"}
            return {
                "id": customer.id,
                "email": customer.email,
                "full_name": customer.full_name,
                "account_status": customer.account_status,
                "plan": customer.plan,
                "device": customer.device,
                "app_version": customer.app_version,
            }

    return await with_session(_run)


@tool
async def get_customer_device(customer_id: str) -> dict[str, Any]:
    """Get the customer's registered device and app version."""

    async def _run(session):
        with log_tool_call(conversation_id=None, agent="technical", tool="get_customer_device"):
            customer = await customer_service.get_customer(session, customer_id)
            if customer is None:
                return {"error": f"Customer {customer_id} not found"}
            return {
                "customer_id": customer.id,
                "device": customer.device,
                "app_version": customer.app_version,
            }

    return await with_session(_run)


@tool
async def get_subscription(customer_id: str) -> dict[str, Any]:
    """Get the customer's current subscription plan and status."""

    async def _run(session):
        with log_tool_call(conversation_id=None, agent="billing", tool="get_subscription"):
            status = await customer_service.get_account_status(session, customer_id)
            if status is None:
                return {"error": f"Customer {customer_id} not found"}
            return {
                "customer_id": customer_id,
                "plan": status["plan"],
                "account_status": status["account_status"],
            }

    return await with_session(_run)
