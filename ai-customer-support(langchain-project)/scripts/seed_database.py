"""Seed demo customers, transactions, and tickets."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

# Ensure project root is importable when run as a script
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.session import AsyncSessionLocal, init_db
from app.models.customer import Customer
from app.models.ticket import Ticket
from app.models.transaction import Transaction


async def seed() -> None:
    Path("./data").mkdir(parents=True, exist_ok=True)
    await init_db()

    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(Customer).limit(1))
        if existing.scalar_one_or_none() is not None:
            print("Database already seeded — skipping.")
            return

        now = datetime.now(UTC)

        customers = [
            Customer(
                id="CUST-001",
                email="alice@example.com",
                full_name="Alice Johnson",
                account_status="active",
                plan="pro",
                device="iPhone 15",
                app_version="3.2.1",
                notes="Has duplicate subscription charge scenario",
            ),
            Customer(
                id="CUST-002",
                email="bob@example.com",
                full_name="Bob Smith",
                account_status="active",
                plan="basic",
                device="Pixel 8",
                app_version="3.2.0",
                notes="Failed payment + password reset scenarios",
            ),
            Customer(
                id="CUST-003",
                email="carol@example.com",
                full_name="Carol Lee",
                account_status="active",
                plan="enterprise",
                device="Samsung Galaxy S24",
                app_version="3.1.9",
                notes="Technical crash when uploading PDF",
            ),
        ]
        session.add_all(customers)

        transactions = [
            # CUST-001: duplicate Pro Monthly charges on the same day
            Transaction(
                id="TX-1001",
                customer_id="CUST-001",
                amount=Decimal("29.99"),
                currency="USD",
                status="succeeded",
                description="Pro Monthly Subscription",
                invoice_id="INV-5001",
                created_at=now - timedelta(days=1, hours=2),
            ),
            Transaction(
                id="TX-1002",
                customer_id="CUST-001",
                amount=Decimal("29.99"),
                currency="USD",
                status="succeeded",
                description="Pro Monthly Subscription",
                invoice_id="INV-5001",
                created_at=now - timedelta(days=1, hours=1),
            ),
            Transaction(
                id="TX-1003",
                customer_id="CUST-001",
                amount=Decimal("29.99"),
                currency="USD",
                status="succeeded",
                description="Pro Monthly Subscription",
                invoice_id="INV-4900",
                created_at=now - timedelta(days=31),
            ),
            # CUST-002: failed payment
            Transaction(
                id="TX-2001",
                customer_id="CUST-002",
                amount=Decimal("9.99"),
                currency="USD",
                status="failed",
                description="Basic Monthly Subscription",
                invoice_id="INV-6001",
                created_at=now - timedelta(days=2),
            ),
            Transaction(
                id="TX-2002",
                customer_id="CUST-002",
                amount=Decimal("9.99"),
                currency="USD",
                status="succeeded",
                description="Basic Monthly Subscription",
                invoice_id="INV-5900",
                created_at=now - timedelta(days=32),
            ),
            # CUST-003: normal billing
            Transaction(
                id="TX-3001",
                customer_id="CUST-003",
                amount=Decimal("99.00"),
                currency="USD",
                status="succeeded",
                description="Enterprise Monthly Subscription",
                invoice_id="INV-7001",
                created_at=now - timedelta(days=5),
            ),
        ]
        session.add_all(transactions)

        tickets = [
            Ticket(
                id="TICKET-1001",
                customer_id="CUST-002",
                category="billing",
                priority="medium",
                status="resolved",
                subject="Previous failed payment inquiry",
                description="Customer asked about a failed card charge last month.",
                created_by_agent="billing",
            ),
            Ticket(
                id="TICKET-1002",
                customer_id="CUST-003",
                category="technical",
                priority="high",
                status="open",
                subject="App crash on PDF upload",
                description="Crash reproduced on Android when uploading large PDFs.",
                created_by_agent="technical",
            ),
        ]
        session.add_all(tickets)
        await session.commit()
        print("Seed complete: 3 customers, 6 transactions, 2 tickets.")


if __name__ == "__main__":
    asyncio.run(seed())
