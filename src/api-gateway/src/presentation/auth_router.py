from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from uuid6 import uuid7

from infrastructure.database import SessionLocal
from infrastructure.orm_models import UserORM, UserRole, TenantORM, TenantType
from sqlalchemy_utils import Ltree
from use_cases.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str
    role: UserRole = UserRole.STUDENT
    tenant_id: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    tenant_id: str
    display_name: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/login",
    response_model=TokenResponse,
    summary="Login with email and password",
    description="Authenticates a user and returns a JWT access token along with user details. The token should be passed as `Bearer <token>` in the `Authorization` header for subsequent requests.")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserORM).filter(UserORM.email == body.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not user.hashed_password:
        raise HTTPException(status_code=401, detail="Password login not enabled for this account. Use SSO.")

    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(user.id, user.role.value, user.tenant_id)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        role=user.role.value,
        tenant_id=str(user.tenant_id),
        display_name=user.display_name or user.email,
    )


@router.post("/register",
    response_model=TokenResponse,
    status_code=201,
    summary="Register a new user",
    description="""
    Creates a new user account with the specified role.
    If no tenant_id is provided, a new tenant is automatically created for the user's domain.
    On success, returns a JWT access token and user details.
    """)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(UserORM).filter(UserORM.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    if body.tenant_id:
        tenant = db.query(TenantORM).filter(TenantORM.id == body.tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found.")
        tenant_id = tenant.id
        tenant_path = tenant.path
    else:
        tenant_path = Ltree(body.email.split("@")[-1].replace(".", "_"))
        default_tenant = TenantORM(
            id=uuid7(),
            name=body.email.split("@")[-1],
            type=TenantType.UNIVERSITY,
            compute_credits=500.0,
            subscription_tier="Starter",
            path=tenant_path,
        )
        db.add(default_tenant)
        db.commit()
        db.refresh(default_tenant)
        tenant_id = default_tenant.id

    user = UserORM(
        id=uuid7(),
        email=body.email,
        display_name=body.display_name or body.email.split("@")[0],
        role=body.role,
        tenant_id=tenant_id,
        tenant_path=tenant_path,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.role.value, user.tenant_id)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        role=user.role.value,
        tenant_id=str(user.tenant_id),
        display_name=user.display_name or user.email,
    )
