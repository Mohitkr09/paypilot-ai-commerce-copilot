# app/schemas/auth.py

from pydantic import BaseModel, EmailStr, ConfigDict


# =========================================================
# REGISTER REQUEST
# =========================================================

class RegisterRequest(BaseModel):

    name: str
    email: EmailStr
    password: str


# =========================================================
# LOGIN REQUEST
# =========================================================

class LoginRequest(BaseModel):

    email: EmailStr
    password: str


# =========================================================
# TOKEN RESPONSE
# =========================================================

class TokenResponse(BaseModel):

    access_token: str

    token_type: str = "bearer"

    expires_in: int

    merchant_id: int

    role: str


# =========================================================
# MERCHANT RESPONSE
# =========================================================

class MerchantResponse(BaseModel):

    id: int

    name: str

    email: EmailStr

    role: str

    is_active: bool

    maximum_discount_percent: float

    minimum_margin: float

    auto_payment_limit: float

    bundle_allowed: bool

    model_config = ConfigDict(
        from_attributes=True
    )