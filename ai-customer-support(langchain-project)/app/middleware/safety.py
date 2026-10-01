"""Tool authorization — separate read vs sensitive write operations."""

from __future__ import annotations

READ_TOOLS = frozenset(
    {
        "get_customer",
        "get_subscription",
        "get_transactions",
        "get_invoice",
        "get_account_status",
        "get_customer_device",
        "get_service_status",
        "search_knowledge_base",
    }
)

SENSITIVE_WRITE_TOOLS = frozenset(
    {
        "create_refund_request",
        "prepare_email_change",
        "delete_account_request",
        "create_large_compensation",
    }
)

SAFE_WRITE_TOOLS = frozenset(
    {
        "create_support_ticket",
        "create_password_reset",
    }
)

ALL_TOOLS = READ_TOOLS | SENSITIVE_WRITE_TOOLS | SAFE_WRITE_TOOLS


def is_sensitive_write(tool_name: str) -> bool:
    return tool_name in SENSITIVE_WRITE_TOOLS


def is_authorized(tool_name: str, *, allow_sensitive: bool = False) -> bool:
    if tool_name not in ALL_TOOLS:
        return False
    if is_sensitive_write(tool_name) and not allow_sensitive:
        return False
    return True
