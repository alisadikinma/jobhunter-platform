"""Admin CRUD for the Firecrawl account pool — mirror of /api/apify."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.firecrawl_account import FirecrawlAccount
from app.models.user import User
from app.schemas.firecrawl import (
    FirecrawlAccountBulkCreate,
    FirecrawlAccountCreate,
    FirecrawlAccountResponse,
    FirecrawlAccountUpdate,
    FirecrawlTestResult,
)
from app.services import firecrawl_service
from app.services.encryption import decrypt_token, encrypt_token, mask_token

router = APIRouter(prefix="/api/firecrawl", tags=["firecrawl"])


def _to_response(account: FirecrawlAccount) -> FirecrawlAccountResponse:
    if account.api_token:
        try:
            plain = decrypt_token(account.api_token)
            token_masked = mask_token(plain) if plain else ""
        except Exception:
            token_masked = "****"
    else:
        token_masked = ""
    return FirecrawlAccountResponse(
        id=account.id,
        label=account.label,
        email=account.email or "",
        api_url=account.api_url,
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


@router.get("/accounts", response_model=list[FirecrawlAccountResponse])
def list_accounts(
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    accounts = (
        db.query(FirecrawlAccount)
        .order_by(FirecrawlAccount.priority.asc(), FirecrawlAccount.id.asc())
        .all()
    )
    return [_to_response(a) for a in accounts]


@router.post(
    "/accounts",
    response_model=FirecrawlAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_account(
    body: FirecrawlAccountCreate,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    account = FirecrawlAccount(
        label=body.label,
        email=body.email,
        api_url=body.api_url,
        api_token=encrypt_token(body.api_token) if body.api_token else "",
        priority=body.priority,
        monthly_credit_usd=body.monthly_credit_usd,
        notes=body.notes,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return _to_response(account)


@router.post(
    "/accounts/bulk",
    response_model=list[FirecrawlAccountResponse],
    status_code=status.HTTP_201_CREATED,
)
def bulk_create(
    body: FirecrawlAccountBulkCreate,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    """One-shot import. Each line: `label,api_url,token[,email]`."""
    created: list[FirecrawlAccount] = []
    for raw in body.lines:
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) < 3 or not parts[0] or not parts[1]:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid line (expected 'label,api_url,token[,email]'): {raw!r}",
            )
        label = parts[0]
        api_url = parts[1]
        token = parts[2] if len(parts) > 2 else ""
        email = parts[3] if len(parts) > 3 else ""

        account = FirecrawlAccount(
            label=label,
            email=email,
            api_url=api_url,
            api_token=encrypt_token(token) if token else "",
        )
        db.add(account)
        created.append(account)
    db.commit()
    for account in created:
        db.refresh(account)
    return [_to_response(a) for a in created]


@router.patch("/accounts/{account_id}", response_model=FirecrawlAccountResponse)
def update_account(
    account_id: int,
    body: FirecrawlAccountUpdate,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    account = db.get(FirecrawlAccount, account_id)
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
    account = db.get(FirecrawlAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(account)
    db.commit()


@router.post("/accounts/{account_id}/test", response_model=FirecrawlTestResult)
def test_connection(
    account_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    ok, message, sample_chars = firecrawl_service.test_account_connection(db, account_id)
    return FirecrawlTestResult(ok=ok, message=message, sample_chars=sample_chars)
