from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select

# from app.schemas import User, UserCreate
from app.models.transaction import Transaction, TransactionRead
from app.models.risk import AccountRiskStatus
from app.models.user import User, UserCreate, UserRead, UserUpdate
from app.service.store import USERS
from app.db import get_session
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


@router.post("", status_code=201, response_model=UserRead)
async def create_user(body: UserCreate, db: Session = Depends(get_session)) -> User:
    """Create a user with a mock balance and mock transaction history."""
    user = User.model_validate(body)
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"New user added")

    # logger.info(f"Adding mock transactions...")
    # # mock_past_transactions(user_id=user.id)
    return user

def _read(user: User, risk: AccountRiskStatus | None) -> UserRead:
    extra = {"account_status": risk.status, "risk_tier": risk.risk_tier} if risk else {}
    return UserRead.model_validate(user, update=extra)


@router.get("/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_session)) -> UserRead:
    """Return the user with their account status and risk tier."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "user not found")
    risk = db.exec(select(AccountRiskStatus).where(AccountRiskStatus.user_id == user_id)).first()
    return _read(user, risk)

@router.get("/{user_id}/transactions", response_model=list[TransactionRead])
async def list_user_transactions(user_id: int, db: Session = Depends(get_session)):
    return db.exec(
        select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.created_at.desc())
    ).all()

@router.get("/")
async def list_users(db: Session = Depends(get_session)) -> list[UserRead]:
    # all = db.exec(select(User).where(User.name != "")).all()
    # all = db.exec(select(User).where(User.name != "")).all()
    # all = db.exec(select(User).where(User.name != "")).all()
    rows = db.exec(
        select(User, AccountRiskStatus)
        .join(AccountRiskStatus, AccountRiskStatus.user_id == User.id, isouter=True)
        .order_by(User.id)
    ).all()
    if not rows:
        raise HTTPException(404, "No users present")
    return [_read(u, r) for u, r in rows]