import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.account import Account, AccountStatus
from app.schemas.account import AccountCreate, AccountRead

router = APIRouter()


@router.post("/", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def add_account(payload: AccountCreate, db: AsyncSession = Depends(get_db)):
    """
    Add an Instagram account to the pool.
    session_json must be obtained via the add_account.py script (never sends password).
    """
    # Check for duplicates
    existing = await db.execute(select(Account).where(Account.username == payload.username))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Account @{payload.username} already exists",
        )

    account = Account(
        username=payload.username.lstrip("@"),
        session_json=payload.session_json,
        proxy_url=payload.proxy_url,
        status=AccountStatus.active,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.get("/", response_model=list[AccountRead])
async def list_accounts(db: AsyncSession = Depends(get_db)):
    """List all accounts in the pool with their current status."""
    result = await db.execute(select(Account).order_by(Account.created_at.desc()))
    return result.scalars().all()


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_account(account_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Remove an Instagram account from the pool."""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)
    await db.commit()
