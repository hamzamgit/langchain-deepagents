"""Customer API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.schemas.customer import CustomerRead
from app.services import customer_service

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerRead])
async def list_customers(
    session: AsyncSession = Depends(get_db_session),
) -> list[CustomerRead]:
    customers = await customer_service.list_customers(session)
    return [CustomerRead.model_validate(c) for c in customers]


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(
    customer_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> CustomerRead:
    customer = await customer_service.get_customer(session, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return CustomerRead.model_validate(customer)
