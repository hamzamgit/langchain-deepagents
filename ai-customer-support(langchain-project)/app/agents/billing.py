"""Billing agent — investigates charges and prepares refunds for approval."""

from __future__ import annotations

from typing import Any

from app.graph.state import SupportState
from app.middleware.logging import log_agent_step
from app.services import billing_service
from app.tools._session import with_session
from app.tools.billing_tools import create_refund_request, get_transactions
from app.tools.customer_tools import get_customer, get_subscription


async def run_billing_agent(state: SupportState) -> dict[str, Any]:
    customer_id = state["customer_id"]
    conversation_id = state["conversation_id"]
    message = state.get("message", "")
    tool_results: list[dict[str, Any]] = list(state.get("tool_results") or [])

    log_agent_step(
        conversation_id=conversation_id,
        agent="billing",
        step="investigate",
        details={"message": message[:200]},
    )

    customer = await get_customer.ainvoke({"customer_id": customer_id})
    tool_results.append({"tool": "get_customer", "result": customer})

    subscription = await get_subscription.ainvoke({"customer_id": customer_id})
    tool_results.append({"tool": "get_subscription", "result": subscription})

    transactions = await get_transactions.ainvoke({"customer_id": customer_id})
    tool_results.append({"tool": "get_transactions", "result": transactions})

    if isinstance(transactions, dict) and transactions.get("error"):
        return {
            "tool_results": tool_results,
            "assigned_agent": "billing",
            "resolution": {
                "resolved": False,
                "requires_approval": False,
                "resolution_summary": "Could not load transactions.",
                "customer_response_draft": (
                    "I couldn't retrieve your billing history right now. "
                    "Please try again shortly or wait while we escalate."
                ),
            },
            "requires_human": False,
            "errors": [str(transactions.get("error"))],
        }

    # Detect duplicates using service logic on live DB rows
    async def _dupes(session):
        txns = await billing_service.get_transactions(session, customer_id)
        return billing_service.find_duplicate_charges(txns)

    duplicates = await with_session(_dupes)
    tool_results.append({"tool": "find_duplicate_charges", "result": duplicates})

    text = message.lower()
    wants_refund = any(k in text for k in ("twice", "duplicate", "refund", "charged"))

    if duplicates and wants_refund:
        dup = duplicates[0]
        # Refund the later duplicate charge
        refund_txn = dup["transaction_ids"][-1]
        refund = await create_refund_request.ainvoke(
            {
                "customer_id": customer_id,
                "conversation_id": conversation_id,
                "transaction_id": refund_txn,
                "amount": dup["amount"],
                "reason": (
                    f"Duplicate charge detected: {dup['transaction_ids']} "
                    f"for {dup['description']} on {dup['date']}"
                ),
            }
        )
        tool_results.append({"tool": "create_refund_request", "result": refund})

        return {
            "tool_results": tool_results,
            "assigned_agent": "billing",
            "requires_human": True,
            "approval_id": refund.get("approval_id"),
            "approval_status": "pending",
            "resolution": {
                "resolved": False,
                "requires_approval": True,
                "approval_action_type": "refund",
                "approval_payload": refund.get("payload", {}),
                "resolution_summary": (
                    f"Detected duplicate charge; refund of ${dup['amount']} "
                    f"for {refund_txn} awaiting approval."
                ),
                "customer_response_draft": (
                    f"I found a duplicate charge of ${dup['amount']} "
                    f"({', '.join(dup['transaction_ids'])}). "
                    "I've prepared a refund request for human review. "
                    "You'll receive confirmation once it's approved."
                ),
            },
        }

    # Failed payment inquiry
    failed = [t for t in transactions if isinstance(t, dict) and t.get("status") == "failed"]
    if failed:
        return {
            "tool_results": tool_results,
            "assigned_agent": "billing",
            "requires_human": False,
            "resolution": {
                "resolved": True,
                "requires_approval": False,
                "resolution_summary": f"Found failed payment {failed[0]['id']}.",
                "customer_response_draft": (
                    f"I see a failed payment ({failed[0]['id']}) for "
                    f"${failed[0]['amount']} — {failed[0]['description']}. "
                    "Please update your payment method under Account → Billing. "
                    "We automatically retry failed payments up to 3 times over 7 days."
                ),
            },
        }

    return {
        "tool_results": tool_results,
        "assigned_agent": "billing",
        "requires_human": False,
        "resolution": {
            "resolved": True,
            "requires_approval": False,
            "resolution_summary": "Reviewed billing history; no duplicate charges found.",
            "customer_response_draft": (
                "I reviewed your recent transactions and didn't find a duplicate charge. "
                "Your current plan is "
                f"{subscription.get('plan', 'unknown')}. "
                "If you can share an invoice or transaction ID, I can dig deeper."
            ),
        },
    }
