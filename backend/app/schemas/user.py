from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)


# =========================================================
# USER BASE
# =========================================================

class UserBase(BaseModel):
    """
    Common user fields.
    """

    username: str = Field(
        ...,
        min_length=3,
        max_length=100,
    )

    email: EmailStr

    role: str = Field(
        default="USER",
        max_length=50,
    )

    merchant_id: int | None = None


# =========================================================
# USER CREATE
# =========================================================

class UserCreate(UserBase):
    """
    Used when creating/registering a user.
    """

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )


# =========================================================
# USER UPDATE
# =========================================================

class UserUpdate(BaseModel):
    """
    Used when updating an existing user.

    All fields are optional.
    """

    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
    )

    email: EmailStr | None = None

    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
    )

    role: str | None = Field(
        default=None,
        max_length=50,
    )

    merchant_id: int | None = None

    is_active: bool | None = None


# =========================================================
# USER RESPONSE
# =========================================================

class UserResponse(BaseModel):
    """
    Public user response.

    IMPORTANT:
    password and password_hash are intentionally
    NOT included.
    """

    id: int

    username: str

    email: EmailStr

    role: str

    merchant_id: int | None = None

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# LOGIN REQUEST
# =========================================================

class LoginRequest(BaseModel):
    """
    Login credentials.
    """

    username: str

    password: str


# =========================================================
# TOKEN RESPONSE
# =========================================================

class TokenResponse(BaseModel):
    """
    JWT authentication response.
    """

    access_token: str

    token_type: str = "bearer"

    user: UserResponse


# =========================================================
# TOKEN DATA
# =========================================================

class TokenData(BaseModel):
    """
    Data extracted from JWT token.
    """

    user_id: int

    username: str

    role: str

    merchant_id: int | None = None