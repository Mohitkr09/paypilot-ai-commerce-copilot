# app/auth/security.py

import os

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext


# =========================================================
# CONFIGURATION
# =========================================================

# IMPORTANT:
# Set SECRET_KEY in your .env file in production.
#
# Example:
#
# SECRET_KEY=your-long-random-secret-key
#
# Never use the development fallback in production.

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "paypilot-development-secret-change-this-before-deployment",
)

ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256",
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "60",
    )
)


# =========================================================
# PASSWORD HASHING
# =========================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


# =========================================================
# HASH PASSWORD
# =========================================================

def hash_password(
    password: str,
) -> str:
    """
    Hash a plain-text password.

    The original password must NEVER be stored
    in the database.
    """

    if not password:
        raise ValueError(
            "Password cannot be empty."
        )

    return pwd_context.hash(
        password
    )


# =========================================================
# VERIFY PASSWORD
# =========================================================

def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verify a plain-text password against
    the stored password hash.
    """

    if not plain_password:
        return False

    if not hashed_password:
        return False

    try:

        return pwd_context.verify(
            plain_password,
            hashed_password,
        )

    except Exception:

        return False


# =========================================================
# CREATE ACCESS TOKEN
# =========================================================

def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[
        timedelta
    ] = None,
) -> str:
    """
    Create a JWT access token.

    Example:

        {
            "sub": "1",
            "user_id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "role": "ADMIN",
            "merchant_id": null
        }
    """

    if not data:

        raise ValueError(
            "Token data cannot be empty."
        )

    to_encode = data.copy()

    # -----------------------------------------------------
    # CURRENT UTC TIME
    # -----------------------------------------------------

    now = datetime.now(
        timezone.utc
    )

    # -----------------------------------------------------
    # TOKEN EXPIRATION
    # -----------------------------------------------------

    if expires_delta:

        expire = (
            now
            + expires_delta
        )

    else:

        expire = (
            now
            + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )
        )

    # -----------------------------------------------------
    # STANDARD JWT CLAIMS
    # -----------------------------------------------------

    to_encode.update(
        {
            "iat": now,
            "exp": expire,
        }
    )

    # -----------------------------------------------------
    # ENCODE JWT
    # -----------------------------------------------------

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return encoded_jwt


# =========================================================
# CREATE USER ACCESS TOKEN
# =========================================================

def create_user_access_token(
    user_id: int,
    username: str,
    email: str,
    role: str,
    merchant_id: Optional[int] = None,
) -> str:
    """
    Create a JWT for an authenticated user.

    The token contains both identity and authorization
    information.
    """

    if user_id is None:

        raise ValueError(
            "user_id is required."
        )

    if user_id <= 0:

        raise ValueError(
            "Invalid user_id."
        )

    if not username:

        raise ValueError(
            "username is required."
        )

    if not email:

        raise ValueError(
            "email is required."
        )

    if not role:

        raise ValueError(
            "role is required."
        )

    normalized_role = (
        str(role)
        .strip()
        .upper()
    )

    # -----------------------------------------------------
    # PAYLOAD
    # -----------------------------------------------------

    payload = {

        # JWT subject
        "sub": str(
            user_id
        ),

        # Explicit user identity
        "user_id": user_id,

        "username": username,

        "email": email,

        # Authorization role
        "role": normalized_role,

        # Merchant ownership
        "merchant_id": merchant_id,
    }

    return create_access_token(
        payload
    )


# =========================================================
# CREATE MERCHANT ACCESS TOKEN
# =========================================================

def create_merchant_access_token(
    merchant_id: int,
    email: str,
    role: str,
) -> str:
    """
    Backward-compatible merchant token.

    This is useful if older parts of the PayPilot
    application still authenticate directly using
    merchant identity.

    New authentication should preferably use
    create_user_access_token().
    """

    if merchant_id is None:

        raise ValueError(
            "merchant_id is required."
        )

    if merchant_id <= 0:

        raise ValueError(
            "Invalid merchant_id."
        )

    if not email:

        raise ValueError(
            "email is required."
        )

    if not role:

        raise ValueError(
            "role is required."
        )

    normalized_role = (
        str(role)
        .strip()
        .upper()
    )

    payload = {

        # Keep merchant ID as subject
        # for backward compatibility.
        "sub": str(
            merchant_id
        ),

        "merchant_id": merchant_id,

        "email": email,

        "role": normalized_role,
    }

    return create_access_token(
        payload
    )


# =========================================================
# DECODE ACCESS TOKEN
# =========================================================

def decode_access_token(
    token: str,
) -> Optional[
    dict[str, Any]
]:
    """
    Decode and validate a JWT.

    Returns:
        JWT payload when valid.

    Returns:
        None when invalid or expired.
    """

    if not token:

        return None

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[
                ALGORITHM
            ],
        )

        return payload

    except JWTError:

        return None

    except Exception:

        return None


# =========================================================
# GET USER ID FROM TOKEN
# =========================================================

def get_user_id_from_token(
    token: str,
) -> Optional[int]:
    """
    Extract user ID from JWT.
    """

    payload = decode_access_token(
        token
    )

    if not payload:

        return None

    # -----------------------------------------------------
    # Prefer explicit user_id
    # -----------------------------------------------------

    user_id = payload.get(
        "user_id"
    )

    if user_id is not None:

        try:

            user_id = int(
                user_id
            )

        except (
            TypeError,
            ValueError,
        ):

            return None

        if user_id <= 0:

            return None

        return user_id

    # -----------------------------------------------------
    # Fallback to JWT subject
    # -----------------------------------------------------

    subject = payload.get(
        "sub"
    )

    if subject is None:

        return None

    try:

        user_id = int(
            subject
        )

    except (
        TypeError,
        ValueError,
    ):

        return None

    if user_id <= 0:

        return None

    return user_id


# =========================================================
# GET MERCHANT ID FROM TOKEN
# =========================================================

def get_merchant_id_from_token(
    token: str,
) -> Optional[int]:
    """
    Extract merchant ID from JWT.
    """

    payload = decode_access_token(
        token
    )

    if not payload:

        return None

    # -----------------------------------------------------
    # Prefer explicit merchant_id
    # -----------------------------------------------------

    merchant_id = payload.get(
        "merchant_id"
    )

    if merchant_id is not None:

        try:

            merchant_id = int(
                merchant_id
            )

        except (
            TypeError,
            ValueError,
        ):

            return None

        if merchant_id <= 0:

            return None

        return merchant_id

    # -----------------------------------------------------
    # Backward compatibility
    #
    # Older merchant tokens use:
    #
    #     sub = merchant_id
    # -----------------------------------------------------

    subject = payload.get(
        "sub"
    )

    if subject is None:

        return None

    try:

        merchant_id = int(
            subject
        )

    except (
        TypeError,
        ValueError,
    ):

        return None

    if merchant_id <= 0:

        return None

    return merchant_id


# =========================================================
# GET ROLE FROM TOKEN
# =========================================================

def get_role_from_token(
    token: str,
) -> Optional[str]:
    """
    Extract authorization role from JWT.
    """

    payload = decode_access_token(
        token
    )

    if not payload:

        return None

    role = payload.get(
        "role"
    )

    if not role:

        return None

    return (
        str(role)
        .strip()
        .upper()
    )


# =========================================================
# GET USERNAME FROM TOKEN
# =========================================================

def get_username_from_token(
    token: str,
) -> Optional[str]:
    """
    Extract username from JWT.
    """

    payload = decode_access_token(
        token
    )

    if not payload:

        return None

    username = payload.get(
        "username"
    )

    if not username:

        return None

    return (
        str(username)
        .strip()
    )


# =========================================================
# GET EMAIL FROM TOKEN
# =========================================================

def get_email_from_token(
    token: str,
) -> Optional[str]:
    """
    Extract email from JWT.
    """

    payload = decode_access_token(
        token
    )

    if not payload:

        return None

    email = payload.get(
        "email"
    )

    if not email:

        return None

    return (
        str(email)
        .strip()
        .lower()
    )


# =========================================================
# GET COMPLETE TOKEN PAYLOAD
# =========================================================

def get_token_payload(
    token: str,
) -> dict[str, Any]:
    """
    Return the complete validated JWT payload.

    Raises:
        ValueError if the token is invalid.
    """

    payload = decode_access_token(
        token
    )

    if not payload:

        raise ValueError(
            "Invalid or expired access token."
        )

    return payload


# =========================================================
# TOKEN VALIDATION
# =========================================================

def validate_access_token(
    token: str,
) -> dict[str, Any]:
    """
    Validate access token and return its payload.

    This validates:
        - JWT signature
        - expiration
        - user identity
        - role

    Raises:
        ValueError when token is invalid.
    """

    payload = decode_access_token(
        token
    )

    if not payload:

        raise ValueError(
            "Invalid or expired access token."
        )

    # -----------------------------------------------------
    # USER ID
    # -----------------------------------------------------

    user_id = payload.get(
        "user_id"
    )

    subject = payload.get(
        "sub"
    )

    # New user token
    if user_id is not None:

        try:

            user_id = int(
                user_id
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                "Invalid user identity in access token."
            )

        if user_id <= 0:

            raise ValueError(
                "Invalid user identity in access token."
            )

    # Old merchant token
    elif subject:

        try:

            merchant_id = int(
                subject
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                "Invalid identity in access token."
            )

        if merchant_id <= 0:

            raise ValueError(
                "Invalid identity in access token."
            )

    else:

        raise ValueError(
            "Access token does not contain identity."
        )

    # -----------------------------------------------------
    # ROLE
    # -----------------------------------------------------

    role = payload.get(
        "role"
    )

    if not role:

        raise ValueError(
            "Access token does not contain authorization role."
        )

    role = (
        str(role)
        .strip()
        .upper()
    )

    # -----------------------------------------------------
    # EMAIL
    # -----------------------------------------------------

    email = payload.get(
        "email"
    )

    if not email:

        raise ValueError(
            "Access token does not contain email."
        )

    # -----------------------------------------------------
    # NORMALIZE RETURN PAYLOAD
    # -----------------------------------------------------

    payload["role"] = role

    payload["email"] = (
        str(email)
        .strip()
        .lower()
    )

    return payload