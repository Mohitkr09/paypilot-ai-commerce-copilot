from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
)

from app.db.database import Base


class Order(Base):

    __tablename__ = "orders"

    # =========================================================
    # PRIMARY KEY
    # =========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # =========================================================
    # RELATIONSHIPS
    # =========================================================

    merchant_id = Column(
        Integer,
        ForeignKey("merchants.id"),
        nullable=False,
        index=True,
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        index=True,
    )

    # =========================================================
    # ORDER INFORMATION
    # =========================================================

    quantity = Column(
        Integer,
        nullable=False,
    )

    # =========================================================
    # AMOUNT INFORMATION
    # =========================================================

    original_amount = Column(
        Float,
        nullable=False,
    )

    discount_percent = Column(
        Float,
        nullable=False,
    )

    discount_amount = Column(
        Float,
        nullable=False,
    )

    final_amount = Column(
        Float,
        nullable=False,
    )

    # =========================================================
    # ORDER DECISION
    # =========================================================
    #
    # Possible states:
    #
    # PENDING
    # APPROVED
    # BLOCKED
    # MANUAL_REVIEW_REQUIRED
    # REJECTED
    #
    # =========================================================

    status = Column(
        String(50),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        index=True,
    )

    # =========================================================
    # AI RISK INFORMATION
    # =========================================================

    risk_score = Column(
        Float,
        nullable=True,
    )

    risk_level = Column(
        String(50),
        nullable=True,
    )

    risk_reason = Column(
        Text,
        nullable=True,
    )

    # =========================================================
    # STRUCTURED AI RISK FACTORS
    # =========================================================

    risk_factors = Column(
        Text,
        nullable=True,
    )

    # =========================================================
    # HUMAN-READABLE AI EXPLANATION
    # =========================================================

    ai_explanation = Column(
        Text,
        nullable=True,
    )

    # =========================================================
    # PAYMENT INFORMATION
    # =========================================================
    #
    # payment_required:
    #     Whether payment is required for this order.
    #
    # payment_approved:
    #     Whether PayPilot has actually allowed payment.
    #
    # IMPORTANT:
    #
    # A newly-created order must NOT automatically have
    # payment_approved=True.
    #
    # =========================================================

    payment_required = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    payment_approved = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    payment_gate_status = Column(
        String(50),
        nullable=True,
    )

    payment_gate_reason = Column(
        Text,
        nullable=True,
    )

    # =========================================================
    # MANUAL REVIEW INFORMATION
    # =========================================================

    manual_review_required = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        index=True,
    )

    # =========================================================
    # DISCOUNT DECISION
    # =========================================================

    requested_discount_percent = Column(
        Float,
        nullable=True,
    )

    approved_discount_percent = Column(
        Float,
        nullable=True,
    )

    maximum_safe_discount_percent = Column(
        Float,
        nullable=True,
    )

    discount_adjusted = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    # =========================================================
    # FINANCIAL DECISION DETAILS
    # =========================================================

    final_price = Column(
        Float,
        nullable=True,
    )

    final_margin_percent = Column(
        Float,
        nullable=True,
    )

    # =========================================================
    # AI DECISION EXPLANATION
    # =========================================================

    decision_explanation = Column(
        Text,
        nullable=True,
    )

    # =========================================================
    # FINAL AGENT EXPLANATION
    # =========================================================

    final_explanation = Column(
        Text,
        nullable=True,
    )

    # =========================================================
    # AGENT INFORMATION
    # =========================================================

    processed_by = Column(
        String(100),
        nullable=True,
    )

    # =========================================================
    # INVENTORY INFORMATION
    # =========================================================
    #
    # IMPORTANT:
    #
    # Inventory is deducted ONLY once.
    #
    # Manual approval must check this flag before
    # deducting inventory.
    #
    # =========================================================

    inventory_deducted = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    # =========================================================
    # AUDIT INFORMATION
    # =========================================================

    audit_event_type = Column(
        String(100),
        nullable=True,
    )

    audit_performed_by = Column(
        String(100),
        nullable=True,
    )

    # =========================================================
    # ORDER TIMESTAMP
    # =========================================================

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    # =========================================================
    # LAST UPDATED
    # =========================================================

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )