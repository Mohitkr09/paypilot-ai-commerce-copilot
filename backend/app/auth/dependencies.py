# app/auth/dependencies.py

from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.merchant import Merchant

from app.auth.security import (
    validate_access_token,
)


# =========================================================
# HTTP BEARER SECURITY
# =========================================================

security = HTTPBearer(
    auto_error=False
)


# =========================================================
# GET CURRENT MERCHANT
# =========================================================

def get_current_merchant(
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    ),
    db: Session = Depends(get_db),
) -> Merchant:
    """
    Authenticate the current request using JWT.

    Expected header:

        Authorization: Bearer <access_token>

    Returns:
        Authenticated Merchant object.
    """

    # -----------------------------------------------------
    # CHECK AUTHORIZATION HEADER
    # -----------------------------------------------------

    if credentials is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # -----------------------------------------------------
    # GET TOKEN
    # -----------------------------------------------------

    token = credentials.credentials

    if not token:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # -----------------------------------------------------
    # VALIDATE JWT
    # -----------------------------------------------------

    try:

        payload = validate_access_token(
            token
        )

    except ValueError as e:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # -----------------------------------------------------
    # GET MERCHANT ID
    # -----------------------------------------------------

    merchant_id = payload.get(
        "sub"
    )

    if merchant_id is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    try:

        merchant_id = int(
            merchant_id
        )

    except (
        TypeError,
        ValueError,
    ):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid merchant identity.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    if merchant_id <= 0:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid merchant identity.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # -----------------------------------------------------
    # FIND MERCHANT
    # -----------------------------------------------------

    merchant = (
        db.query(Merchant)
        .filter(
            Merchant.id == merchant_id
        )
        .first()
    )

    if merchant is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Merchant account not found.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # -----------------------------------------------------
    # CHECK ACCOUNT STATUS
    # -----------------------------------------------------

    if not bool(
        merchant.is_active
    ):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Merchant account is inactive.",
        )

    # -----------------------------------------------------
    # VERIFY TOKEN EMAIL
    # -----------------------------------------------------

    token_email = payload.get(
        "email"
    )

    if (
        token_email
        and merchant.email
        and str(token_email).strip().lower()
        != str(merchant.email).strip().lower()
    ):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is invalid.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    # -----------------------------------------------------
    # VERIFY TOKEN ROLE
    # -----------------------------------------------------

    token_role = payload.get(
        "role"
    )

    merchant_role = (
        str(
            merchant.role or "merchant"
        )
        .strip()
        .lower()
    )

    if (
        token_role
        and str(token_role).strip().lower()
        != merchant_role
    ):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is invalid.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    return merchant


# =========================================================
# GET CURRENT USER
# =========================================================

def get_current_user(
    current_merchant: Merchant = Depends(
        get_current_merchant
    ),
) -> Merchant:
    """
    Compatibility dependency.

    The current PayPilot authentication system uses
    Merchant as the authenticated account.

    Product routes can therefore use:

        Depends(get_current_user)

    while internally the authenticated object remains
    a Merchant.
    """

    return current_merchant


# =========================================================
# GET CURRENT ADMIN
# =========================================================

def get_current_admin(
    current_merchant: Merchant = Depends(
        get_current_merchant
    ),
) -> Merchant:
    """
    Require ADMIN authorization.
    """

    role = (
        str(
            current_merchant.role or ""
        )
        .strip()
        .lower()
    )

    if role != "admin":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )

    return current_merchant


# =========================================================
# GET CURRENT MERCHANT ROLE
# =========================================================

def get_current_merchant_role(
    current_merchant: Merchant = Depends(
        get_current_merchant
    ),
) -> Merchant:
    """
    Require MERCHANT authorization.

    ADMIN users are not accepted here.
    """

    role = (
        str(
            current_merchant.role or ""
        )
        .strip()
        .lower()
    )

    if role != "merchant":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Merchant authorization required.",
        )

    return current_merchant


# =========================================================
# GET MERCHANT OR ADMIN
# =========================================================

def get_current_merchant_or_admin(
    current_merchant: Merchant = Depends(
        get_current_merchant
    ),
) -> Merchant:
    """
    Allow both:

        merchant
        admin
    """

    role = (
        str(
            current_merchant.role or ""
        )
        .strip()
        .lower()
    )

    allowed_roles = {
        "merchant",
        "admin",
    }

    if role not in allowed_roles:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You are not authorized "
                "to perform this action."
            ),
        )

    return current_merchant


# =========================================================
# ROLE DEPENDENCY FACTORY
# =========================================================

def require_role(
    *allowed_roles: str,
) -> Callable:
    """
    Create a reusable role-based authorization dependency.

    Example:

        Depends(
            require_role("admin")
        )

    Or:

        Depends(
            require_role(
                "admin",
                "merchant"
            )
        )
    """

    normalized_roles = {
        str(role)
        .strip()
        .lower()
        for role in allowed_roles
    }

    if not normalized_roles:

        raise ValueError(
            "At least one role must be provided."
        )

    def role_checker(
        current_merchant: Merchant = Depends(
            get_current_merchant
        ),
    ) -> Merchant:

        current_role = (
            str(
                current_merchant.role or ""
            )
            .strip()
            .lower()
        )

        if current_role not in normalized_roles:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You are not authorized "
                    "to perform this action."
                ),
            )

        return current_merchant

    return role_checker


# =========================================================
# REQUIRE ADMIN
# =========================================================

require_admin = require_role(
    "admin"
)


# =========================================================
# REQUIRE MERCHANT
# =========================================================

require_merchant = require_role(
    "merchant"
)


# =========================================================
# REQUIRE MERCHANT OR ADMIN
# =========================================================

require_merchant_or_admin = require_role(
    "merchant",
    "admin",
)