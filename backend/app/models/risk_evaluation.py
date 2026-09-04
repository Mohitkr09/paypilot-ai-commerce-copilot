from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    ForeignKey,
    Text,
)

from sqlalchemy.sql import func

from app.db.database import Base


class RiskEvaluation(Base):

    __tablename__ = "risk_evaluations"

    # =========================================================
    # PRIMARY KEY
    # =========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # =========================================================
    # PAYMENT
    # =========================================================

    payment_id = Column(
        Integer,
        ForeignKey("payments.id"),
        nullable=False,
        index=True,
    )

    # =========================================================
    # ORDER
    # =========================================================

    order_id = Column(
        Integer,
        ForeignKey("orders.id"),
        nullable=False,
        index=True,
    )

    # =========================================================
    # MERCHANT
    # =========================================================

    merchant_id = Column(
        Integer,
        ForeignKey("merchants.id"),
        nullable=False,
        index=True,
    )

    # =========================================================
    # TRANSACTION INPUTS
    # =========================================================

    quantity = Column(
        Integer,
        nullable=False,
        default=1,
    )

    discount_percent = Column(
        Numeric(5, 2),
        nullable=False,
        default=0,
    )

    final_amount = Column(
        Numeric(12, 2),
        nullable=False,
    )

    # =========================================================
    # PAYMENT METHOD
    # =========================================================
    #
    # Actual method returned by Razorpay.
    #
    # Examples:
    # card
    # upi
    # netbanking
    # wallet
    # emi
    #
    # =========================================================

    payment_method = Column(
        String(50),
        nullable=True,
        index=True,
    )

    # =========================================================
    # RISK SCORE
    # =========================================================

    risk_score = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # =========================================================
    # RISK LEVEL
    # =========================================================
    #
    # LOW
    # MEDIUM
    # HIGH
    # CRITICAL
    #
    # =========================================================

    risk_level = Column(
        String(20),
        nullable=False,
        default="LOW",
        index=True,
    )

    # =========================================================
    # RISK REASON
    # =========================================================

    risk_reason = Column(
        Text,
        nullable=True,
    )

    # =========================================================
    # BUSINESS DECISION
    # =========================================================
    #
    # APPROVE
    # REVIEW
    # BLOCK
    #
    # =========================================================

    decision = Column(
        String(20),
        nullable=False,
        default="APPROVE",
        index=True,
    )

    # =========================================================
    # TIMESTAMPS
    # =========================================================

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

    # =========================================================
    # DEBUG REPRESENTATION
    # =========================================================

    def __repr__(self):

        return (
            f"<RiskEvaluation("
            f"id={self.id}, "
            f"payment_id={self.payment_id}, "
            f"order_id={self.order_id}, "
            f"merchant_id={self.merchant_id}, "
            f"risk_score={self.risk_score}, "
            f"risk_level='{self.risk_level}', "
            f"decision='{self.decision}', "
            f"payment_method='{self.payment_method}'"
            f")>"
        )