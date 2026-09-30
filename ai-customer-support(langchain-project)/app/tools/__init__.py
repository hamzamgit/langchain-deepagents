"""Tool package exports."""

from app.tools.account_tools import (
    create_password_reset,
    get_account_status,
    prepare_email_change,
)
from app.tools.billing_tools import create_refund_request, get_invoice, get_transactions
from app.tools.customer_tools import get_customer, get_customer_device, get_subscription
from app.tools.ticket_tools import create_support_ticket, get_service_status, search_knowledge_base

BILLING_TOOLS = [get_customer, get_subscription, get_transactions, get_invoice, create_refund_request]
TECHNICAL_TOOLS = [
    search_knowledge_base,
    get_service_status,
    get_customer_device,
    create_support_ticket,
]
ACCOUNT_TOOLS = [get_customer, get_account_status, create_password_reset, prepare_email_change]
GENERAL_TOOLS = [search_knowledge_base, create_support_ticket]

__all__ = [
    "ACCOUNT_TOOLS",
    "BILLING_TOOLS",
    "GENERAL_TOOLS",
    "TECHNICAL_TOOLS",
    "create_password_reset",
    "create_refund_request",
    "create_support_ticket",
    "get_account_status",
    "get_customer",
    "get_customer_device",
    "get_invoice",
    "get_service_status",
    "get_subscription",
    "get_transactions",
    "prepare_email_change",
    "search_knowledge_base",
]
