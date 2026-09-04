from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    Index,
    ForeignKey,
)

from sqlalchemy.sql import func

from app.db.database import Base


class AuditLog(Base):

    __tablename__ = "audit_logs"

    # =========================================================
    # PRIMARY KEY
    # =========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # =========================================================
    # ORDER
    # =========================================================

    order_id = Column(
        Integer,
        nullable=True,
        index=True,
    )

    # =========================================================
    # PAYMENT
    # =========================================================

    payment_id = Column(
        Integer,
        ForeignKey(
            "payments.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # =========================================================
    # MERCHANT
    # =========================================================

    merchant_id = Column(
        Integer,
        nullable=False,
        index=True,
    )

    # =========================================================
    # EVENT
    # =========================================================

    event_type = Column(
        String(100),
        nullable=False,
        index=True,
    )

    # =========================================================
    # MESSAGE
    # =========================================================

    message = Column(
        Text,
        nullable=False,
    )

    # =========================================================
    # STATUS CHANGE
    # =========================================================

    old_status = Column(
        String(100),
        nullable=True,
        index=True,
    )

    new_status = Column(
        String(100),
        nullable=True,
        index=True,
    )

    # =========================================================
    # RISK
    # =========================================================

    risk_score = Column(
        Float,
        nullable=True,
    )

    risk_level = Column(
        String(50),
        nullable=True,
        index=True,
    )

    # =========================================================
    # USER / ADMIN / SYSTEM
    # =========================================================

    performed_by = Column(
        String(100),
        nullable=True,
        index=True,
    )

    # =========================================================
    # TIMESTAMP
    # =========================================================

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # =========================================================
    # COMPOSITE INDEXES
    # =========================================================

    __table_args__ = (

        Index(
            "ix_audit_logs_order_created",
            "order_id",
            "created_at",
        ),

        Index(
            "ix_audit_logs_payment_created",
            "payment_id",
            "created_at",
        ),

        Index(
            "ix_audit_logs_merchant_created",
            "merchant_id",
            "created_at",
        ),

        Index(
            "ix_audit_logs_event_created",
            "event_type",
            "created_at",
        ),
    )