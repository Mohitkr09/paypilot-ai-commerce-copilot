from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)

from sqlalchemy.sql import func

from app.db.database import Base


# =========================================================
# IDEMPOTENCY KEY
# =========================================================
#
# Stores request-level idempotency information.
#
# Purpose:
#
#   - Prevent duplicate orders
#   - Prevent duplicate payment initialization
#   - Safely replay previous responses
#   - Detect reuse of the same key with different payloads
#
#
# Example:
#
#   Merchant 1 sends:
#
#       Idempotency-Key:
#       order-8f123
#
#   First request:
#
#       create order
#       ↓
#       save response
#
#   Second identical request:
#
#       same merchant
#       same idempotency key
#       same request hash
#       ↓
#       return previous result
#
#   Same key + different request:
#
#       BLOCK
#
# =========================================================


class IdempotencyKey(Base):

    __tablename__ = "idempotency_keys"

    # =====================================================
    # PRIMARY KEY
    # =====================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # =====================================================
    # MERCHANT
    # =====================================================
    #
    # Idempotency is scoped per merchant.
    #
    # Two different merchants may safely use the same
    # idempotency key.
    #
    # =====================================================

    merchant_id = Column(
        Integer,
        ForeignKey("merchants.id"),
        nullable=False,
        index=True,
    )

    # =====================================================
    # IDEMPOTENCY KEY
    # =====================================================

    key = Column(
        String(255),
        nullable=False,
    )

    # =====================================================
    # OPERATION
    # =====================================================
    #
    # Examples:
    #
    #   CREATE_ORDER
    #   CREATE_PAYMENT
    #   VERIFY_PAYMENT
    #
    # Keeping operation separately gives us better
    # debugging and safer future expansion.
    #
    # =====================================================

    operation = Column(
        String(50),
        nullable=False,
        index=True,
    )

    # =====================================================
    # REQUEST HASH
    # =====================================================
    #
    # SHA-256 hash of normalized request data.
    #
    # This lets us detect:
    #
    #   Same key + same request
    #       -> replay safely
    #
    #   Same key + different request
    #       -> reject
    #
    # =====================================================

    request_hash = Column(
        String(64),
        nullable=False,
    )

    # =====================================================
    # PROCESSING STATUS
    # =====================================================
    #
    # PROCESSING
    # COMPLETED
    # FAILED
    #
    # PROCESSING is useful for concurrent duplicate
    # requests arriving at almost exactly the same time.
    #
    # =====================================================

    status = Column(
        String(30),
        nullable=False,
        default="PROCESSING",
        index=True,
    )

    # =====================================================
    # RESOURCE INFORMATION
    # =====================================================
    #
    # Examples:
    #
    #   resource_type = ORDER
    #   resource_id   = 130
    #
    # or:
    #
    #   resource_type = PAYMENT
    #   resource_id   = 25
    #
    # =====================================================

    resource_type = Column(
        String(50),
        nullable=True,
        index=True,
    )

    resource_id = Column(
        Integer,
        nullable=True,
        index=True,
    )

    # =====================================================
    # RESPONSE
    # =====================================================
    #
    # JSON response stored as text.
    #
    # We will serialize using json.dumps() in the
    # IdempotencyService.
    #
    # =====================================================

    response_body = Column(
        Text,
        nullable=True,
    )

    response_status_code = Column(
        Integer,
        nullable=True,
    )

    # =====================================================
    # ERROR
    # =====================================================

    error_message = Column(
        Text,
        nullable=True,
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # =====================================================
    # DATABASE CONSTRAINTS
    # =====================================================
    #
    # Important:
    #
    # Same merchant cannot reuse the same key for the
    # same operation.
    #
    # But:
    #
    # Merchant 1:
    #     CREATE_ORDER + abc
    #
    # Merchant 1:
    #     CREATE_PAYMENT + abc
    #
    # can coexist.
    #
    # =====================================================

    __table_args__ = (

        UniqueConstraint(
            "merchant_id",
            "operation",
            "key",
            name=(
                "uq_idempotency_merchant_operation_key"
            ),
        ),

    )

    # =====================================================
    # DEBUG REPRESENTATION
    # =====================================================

    def __repr__(self):

        return (
            f"<IdempotencyKey("
            f"id={self.id}, "
            f"merchant_id={self.merchant_id}, "
            f"operation='{self.operation}', "
            f"key='{self.key}', "
            f"status='{self.status}', "
            f"resource_type='{self.resource_type}', "
            f"resource_id={self.resource_id}"
            f")>"
        )