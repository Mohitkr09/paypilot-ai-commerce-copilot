from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Float,
    Index,
)

from sqlalchemy.orm import relationship

from app.db.database import Base


# =========================================================
# MANUAL REVIEW STATUS
# =========================================================

PENDING = "PENDING"
APPROVED = "APPROVED"
REJECTED = "REJECTED"


# =========================================================
# MANUAL REVIEW MODEL
# =========================================================

class ManualReview(Base):

    __tablename__ = "manual_reviews"

    # =====================================================
    # PRIMARY KEY
    # =====================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # =====================================================
    # ORDER
    # =====================================================

    order_id = Column(
        Integer,
        ForeignKey("orders.id"),
        nullable=False,
        index=True,
    )

    # =====================================================
    # MERCHANT
    # =====================================================

    merchant_id = Column(
        Integer,
        ForeignKey("merchants.id"),
        nullable=False,
        index=True,
    )

    # =====================================================
    # REVIEW INFORMATION
    # =====================================================

    reason = Column(
        Text,
        nullable=False,
    )

    risk_score = Column(
        Float,
        nullable=True,
    )

    risk_level = Column(
        String(50),
        nullable=True,
        index=True,
    )

    # =====================================================
    # REVIEW STATUS
    #
    # PENDING
    # APPROVED
    # REJECTED
    # =====================================================

    status = Column(
        String(50),
        nullable=False,
        default=PENDING,
        index=True,
    )

    # =====================================================
    # ADMIN / HUMAN REVIEW
    # =====================================================

    reviewed_by = Column(
        String(200),
        nullable=True,
    )

    review_comment = Column(
        Text,
        nullable=True,
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    reviewed_at = Column(
        DateTime,
        nullable=True,
    )

    # =====================================================
    # RELATIONSHIPS
    # =====================================================

    order = relationship(
        "Order",
        foreign_keys=[order_id],
    )

    merchant = relationship(
        "Merchant",
        foreign_keys=[merchant_id],
    )

    # =====================================================
    # COMPOSITE INDEXES
    # =====================================================
    #
    # Useful for:
    #
    #   GET /manual-reviews/?status=PENDING
    #
    # and dashboard queries such as:
    #
    #   pending reviews ordered by newest first
    #
    # =====================================================

    __table_args__ = (

        Index(
            "ix_manual_reviews_status_created",
            "status",
            "created_at",
        ),

        Index(
            "ix_manual_reviews_merchant_status",
            "merchant_id",
            "status",
        ),

    )