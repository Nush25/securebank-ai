
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

from backend.app.services.auth_service import (
    register_user,
    login_user,
    logout_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

bearer_scheme = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


@router.post("/register")
def register(request: RegisterRequest):
    try:
        result = register_user(
            email=str(request.email),
            password=request.password,
        )
        result.pop("session", None)
        return result

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post("/login")
def login(request: LoginRequest):
    try:
        return login_user(
            email=str(request.email),
            password=request.password,
        )

    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error))


@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    try:
        return logout_user(credentials.credentials)

    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error))
