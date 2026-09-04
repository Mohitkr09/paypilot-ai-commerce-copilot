# app/routes/auth.py

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session

from app.db.database import get_db

from app.models.merchant import Merchant

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    MerchantResponse,
)

from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

from app.auth.dependencies import (
    get_current_merchant,
)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# =========================================================
# REGISTER
# =========================================================

@router.post(
    "/register",
    response_model=MerchantResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a new merchant.
    """

    try:

        # =================================================
        # NORMALIZE EMAIL
        # =================================================

        email = request.email.lower().strip()

        # =================================================
        # CHECK EXISTING MERCHANT
        # =================================================

        existing_merchant = (
            db.query(Merchant)
            .filter(
                Merchant.email == email
            )
            .first()
        )

        if existing_merchant:

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A merchant with this email "
                    "already exists."
                ),
            )

        # =================================================
        # HASH PASSWORD
        # =================================================

        password_hash = hash_password(
            request.password
        )

        # =================================================
        # CREATE MERCHANT
        # =================================================

        merchant = Merchant(

            name=request.name.strip(),

            email=email,

            password_hash=password_hash,

            # ---------------------------------------------
            # DEFAULT ROLE
            # ---------------------------------------------

            role="merchant",

            # ---------------------------------------------
            # ACCOUNT STATUS
            # ---------------------------------------------

            is_active=True,

            # ---------------------------------------------
            # PAYPILOT POLICY
            # ---------------------------------------------

            maximum_discount_percent=10.0,

            minimum_margin=300.0,

            auto_payment_limit=3000.0,

            bundle_allowed=True,
        )

        # =================================================
        # SAVE
        # =================================================

        db.add(merchant)

        db.commit()

        db.refresh(merchant)

        return merchant

    except HTTPException:

        db.rollback()

        raise

    except Exception as e:

        db.rollback()

        print(
            "REGISTER ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": (
                    "Unable to create merchant account."
                ),
                "error": str(e),
            },
        )


# =========================================================
# LOGIN
# =========================================================

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate merchant and return JWT.
    """

    try:

        # =================================================
        # NORMALIZE EMAIL
        # =================================================

        email = request.email.lower().strip()

        # =================================================
        # FIND MERCHANT
        # =================================================

        merchant = (
            db.query(Merchant)
            .filter(
                Merchant.email == email
            )
            .first()
        )

        # =================================================
        # INVALID LOGIN
        # =================================================

        if not merchant:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={
                    "WWW-Authenticate": "Bearer"
                },
            )

        # =================================================
        # CHECK PASSWORD HASH
        # =================================================

        if not merchant.password_hash:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={
                    "WWW-Authenticate": "Bearer"
                },
            )

        # =================================================
        # VERIFY PASSWORD
        # =================================================

        password_valid = verify_password(
            request.password,
            merchant.password_hash,
        )

        if not password_valid:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={
                    "WWW-Authenticate": "Bearer"
                },
            )

        # =================================================
        # CHECK ACCOUNT ACTIVE
        # =================================================

        if not merchant.is_active:

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Merchant account is inactive.",
            )

        # =================================================
        # NORMALIZE ROLE
        # =================================================

        role = str(
            merchant.role or "merchant"
        ).lower().strip()

        # =================================================
        # CREATE JWT
        # =================================================

        access_token = create_access_token(
            data={
                "sub": str(
                    merchant.id
                ),

                "email": merchant.email,

                "role": role,

                "merchant_id": merchant.id,
            }
        )

        # =================================================
        # RETURN TOKEN
        # =================================================

        return TokenResponse(

            access_token=access_token,

            token_type="bearer",

            expires_in=(
                ACCESS_TOKEN_EXPIRE_MINUTES
                * 60
            ),

            merchant_id=merchant.id,

            role=role,
        )

    except HTTPException:

        raise

    except Exception as e:

        print(
            "LOGIN ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Unable to login.",
                "error": str(e),
            },
        )


# =========================================================
# CURRENT MERCHANT
# =========================================================

@router.get(
    "/me",
    response_model=MerchantResponse,
)
def get_me(
    current_merchant: Merchant = Depends(
        get_current_merchant
    ),
):
    """
    Return currently authenticated merchant.
    """

    return current_merchant