"""Billing / transaction service — controlled access only."""

from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction


async def get_transactions(
    session: AsyncSession,
    customer_id: str,
    *,
    limit: int = 20,
) -> list[Transaction]:
    result = await session.execute(
        select(Transaction)
        .where(Transaction.customer_id == customer_id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_transaction(
    session: AsyncSession, transaction_id: str
) -> Transaction | None:
    result = await session.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    return result.scalar_one_or_none()


async def get_invoice(
    session: AsyncSession, invoice_id: str
) -> dict[str, Any] | None:
    result = await session.execute(
        select(Transaction).where(Transaction.invoice_id == invoice_id)
    )
    transactions = list(result.scalars().all())
    if not transactions:
        return None
    total = sum((t.amount for t in transactions), Decimal("0"))
    return {
        "invoice_id": invoice_id,
        "customer_id": transactions[0].customer_id,
        "transaction_ids": [t.id for t in transactions],
        "total_amount": float(total),
        "currency": transactions[0].currency,
        "statuses": [t.status for t in transactions],
    }


def find_duplicate_charges(transactions: list[Transaction]) -> list[dict[str, Any]]:
    """Detect likely duplicate charges by amount + description + same-day grouping."""
    groups: dict[tuple, list[Transaction]] = {}
    for txn in transactions:
        if txn.status != "succeeded":
            continue
        day = txn.created_at.date().isoformat() if txn.created_at else "unknown"
        key = (str(txn.amount), txn.description, day)
        groups.setdefault(key, []).append(txn)

    duplicates: list[dict[str, Any]] = []
    for key, group in groups.items():
        if len(group) >= 2:
            duplicates.append(
                {
                    "amount": float(group[0].amount),
                    "description": group[0].description,
                    "date": key[2],
                    "transaction_ids": [t.id for t in group],
                    "count": len(group),
                }
            )
    return duplicates


async def create_refund_record(
    session: AsyncSession,
    *,
    customer_id: str,
    original_transaction_id: str,
    amount: Decimal,
    description: str,
) -> Transaction:
    """Record a refund transaction after human approval (demo — not a real PSP)."""
    original = await get_transaction(session, original_transaction_id)
    refund = Transaction(
        id=f"TX-REF-{uuid4().hex[:8].upper()}",
        customer_id=customer_id,
        amount=amount,
        currency=original.currency if original else "USD",
        status="refunded",
        description=description,
        invoice_id=original.invoice_id if original else None,
    )
    session.add(refund)
    if original is not None:
        original.status = "refunded"
    await session.flush()
    return refund
