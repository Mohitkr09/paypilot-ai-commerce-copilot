# app/models/merchant.py

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
)

from app.db.database import Base


# =========================================================
# MERCHANT MODEL
# =========================================================

class Merchant(Base):

    __tablename__ = "merchants"

    # =====================================================
    # PRIMARY KEY
    # =====================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # =====================================================
    # MERCHANT INFORMATION
    # =====================================================

    name = Column(
        String(150),
        nullable=False,
    )

    # =====================================================
    # AUTHENTICATION
    # =====================================================

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # -----------------------------------------------------
    # PASSWORD HASH
    # -----------------------------------------------------
    #
    # NEVER store plain-text passwords.
    #
    # Example:
    #
    # password_hash = "$2b$12$..."
    #
    # The actual password is processed by:
    #
    # app/auth/security.py
    #
    # using bcrypt.
    #
    # -----------------------------------------------------

    password_hash = Column(
        String(255),
        nullable=True,
    )

    # =====================================================
    # AUTHORIZATION
    # =====================================================
    #
    # Supported roles:
    #
    # merchant
    # admin
    #
    # This field is used by:
    #
    # get_current_merchant()
    # require_role()
    # require_admin
    # require_merchant
    #
    # -----------------------------------------------------

    role = Column(
        String(50),
        nullable=False,
        default="merchant",
        server_default="merchant",
        index=True,
    )

    # =====================================================
    # ACCOUNT STATUS
    # =====================================================

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        index=True,
    )

    # =====================================================
    # PAYPILOT MERCHANT POLICY
    # =====================================================

    # Maximum discount merchant is allowed to approve.

    maximum_discount_percent = Column(
        Float,
        nullable=False,
        default=10.0,
    )

    # Minimum margin required for an order.

    minimum_margin = Column(
        Float,
        nullable=False,
        default=300.0,
    )

    # Maximum amount that can automatically
    # pass the payment gate.

    auto_payment_limit = Column(
        Float,
        nullable=False,
        default=3000.0,
    )

    # Whether bundle purchases are allowed.

    bundle_allowed = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # =====================================================
    # REPRESENTATION
    # =====================================================

    def __repr__(self):

        return (
            f"<Merchant("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"email='{self.email}', "
            f"role='{self.role}', "
            f"is_active={self.is_active}"
            f")>"
        )