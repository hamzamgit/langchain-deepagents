"""Customer service — controlled DB access for customer data."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customer import Customer
from app.models.ticket import Ticket
from app.models.transaction import Transaction
from app.schemas.customer import CustomerContext


async def get_customer(session: AsyncSession, customer_id: str) -> Customer | None:
    result = await session.execute(select(Customer).where(Customer.id == customer_id))
    return result.scalar_one_or_none()


async def list_customers(session: AsyncSession) -> list[Customer]:
    result = await session.execute(select(Customer).order_by(Customer.id))
    return list(result.scalars().all())


async def build_customer_context(
    session: AsyncSession, customer_id: str
) -> CustomerContext | None:
    """Load a safe, compact customer context for agent state."""
    result = await session.execute(
        select(Customer)
        .where(Customer.id == customer_id)
        .options(
            selectinload(Customer.tickets),
            selectinload(Customer.transactions),
        )
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return None

    recent_tickets = sorted(customer.tickets, key=lambda t: t.created_at, reverse=True)[:5]
    recent_txns = sorted(customer.transactions, key=lambda t: t.created_at, reverse=True)[:10]

    return CustomerContext(
        customer_id=customer.id,
        email=customer.email,
        full_name=customer.full_name,
        account_status=customer.account_status,
        plan=customer.plan,
        device=customer.device,
        app_version=customer.app_version,
        recent_ticket_ids=[t.id for t in recent_tickets],
        recent_transaction_ids=[t.id for t in recent_txns],
    )


async def get_account_status(session: AsyncSession, customer_id: str) -> dict | None:
    customer = await get_customer(session, customer_id)
    if customer is None:
        return None
    return {
        "customer_id": customer.id,
        "account_status": customer.account_status,
        "plan": customer.plan,
        "email": customer.email,
        "full_name": customer.full_name,
    }
