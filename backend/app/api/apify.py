"""Admin CRUD for the Apify account pool."""
from apify_client import ApifyClient
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.apify_account import ApifyAccount
from app.models.user import User
from app.schemas.apify import (
    ApifyAccountBulkCreate,
    ApifyAccountCreate,
    ApifyAccountResponse,
    ApifyAccountUpdate,
    ApifyTestResult,
)
from app.services.encryption import decrypt_token, encrypt_token, mask_token

router = APIRouter(prefix="/api/apify", tags=["apify"])


def _to_response(account: ApifyAccount) -> ApifyAccountResponse:
    try:
        plain = decrypt_token(account.api_token)
        token_masked = mask_token(plain)
    except Exception:
        token_masked = "****"
    return ApifyAccountResponse(
        id=account.id,
        label=account.label,
        email=account.email,
        token_masked=token_masked,
        priority=account.priority,
        status=account.status,
        monthly_credit_usd=account.monthly_credit_usd,
        credit_used_usd=account.credit_used_usd,
        cooldown_until=account.cooldown_until,
        last_used_at=account.last_used_at,
        last_success_at=account.last_success_at,
        consecutive_failures=account.consecutive_failures or 0,
        last_error=account.last_error,
        notes=account.notes,
        created_at=account.created_at,
    )


@router.get("/accounts", response_model=list[ApifyAccountResponse])
def list_accounts(
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    accounts = db.query(ApifyAccount).order_by(ApifyAccount.priority.asc(), ApifyAccount.id.asc()).all()
    return [_to_response(a) for a in accounts]


@router.post("/accounts", response_model=ApifyAccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    body: ApifyAccountCreate,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    account = ApifyAccount(
        label=body.label,
        email=body.email,
        api_token=encrypt_token(body.api_token),
        priority=body.priority,
        monthly_credit_usd=body.monthly_credit_usd,
        notes=body.notes,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return _to_response(account)


@router.post("/accounts/bulk", response_model=list[ApifyAccountResponse], status_code=status.HTTP_201_CREATED)
def bulk_create(
    body: ApifyAccountBulkCreate,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    created: list[ApifyAccount] = []
    for raw in body.lines:
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) < 3 or not all(parts[:3]):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid line (expected 'label,email,token'): {raw!r}",
            )
        label, email, token = parts[0], parts[1], parts[2]
        account = ApifyAccount(
            label=label,
            email=email,
            api_token=encrypt_token(token),
        )
        db.add(account)
        created.append(account)
    db.commit()
    for account in created:
        db.refresh(account)
    return [_to_response(a) for a in created]


@router.patch("/accounts/{account_id}", response_model=ApifyAccountResponse)
def update_account(
    account_id: int,
    body: ApifyAccountUpdate,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    account = db.get(ApifyAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return _to_response(account)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    account = db.get(ApifyAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(account)
    db.commit()


@router.post("/accounts/{account_id}/test", response_model=ApifyTestResult)
def test_connection(
    account_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    account = db.get(ApifyAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        token = decrypt_token(account.api_token)
        client = ApifyClient(token)
        user_info = client.user("me").get()
        username = (user_info or {}).get("username", "unknown")
        return ApifyTestResult(ok=True, message=f"Connected as {username}")
    except Exception as e:
        return ApifyTestResult(ok=False, message=str(e))
