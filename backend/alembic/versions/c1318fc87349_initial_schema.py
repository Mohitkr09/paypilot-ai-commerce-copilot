"""initial schema

Revision ID: c1318fc87349
Revises:
Create Date: 2026-08-29 13:30:57.335773
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# =========================================================
# REVISION
# =========================================================

revision: str = "c1318fc87349"

down_revision: Union[str, Sequence[str], None] = None

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


# =========================================================
# UPGRADE
# =========================================================

def upgrade() -> None:

    # =====================================================
    # AUDIT LOGS
    # =====================================================

    op.alter_column(
        "audit_logs",
        "created_at",
        existing_type=sa.TIMESTAMP(),
        nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    op.create_index(
        "ix_audit_logs_created_at",
        "audit_logs",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        "ix_audit_logs_event_type",
        "audit_logs",
        ["event_type"],
        unique=False,
    )

    op.create_index(
        "ix_audit_logs_id",
        "audit_logs",
        ["id"],
        unique=False,
    )

    op.create_index(
        "ix_audit_logs_merchant_created",
        "audit_logs",
        ["merchant_id", "created_at"],
        unique=False,
    )

    op.create_index(
        "ix_audit_logs_merchant_id",
        "audit_logs",
        ["merchant_id"],
        unique=False,
    )

    op.create_index(
        "ix_audit_logs_new_status",
        "audit_logs",
        ["new_status"],
        unique=False,
    )

    op.create_index(
        "ix_audit_logs_old_status",
        "audit_logs",
        ["old_status"],
        unique=False,
    )

    op.create_index(
        "ix_audit_logs_order_created",
        "audit_logs",
        ["order_id", "created_at"],
        unique=False,
    )

    op.create_index(
        "ix_audit_logs_order_id",
        "audit_logs",
        ["order_id"],
        unique=False,
    )

    op.create_index(
        "ix_audit_logs_performed_by",
        "audit_logs",
        ["performed_by"],
        unique=False,
    )

    op.create_index(
        "ix_audit_logs_risk_level",
        "audit_logs",
        ["risk_level"],
        unique=False,
    )

    # =====================================================
    # MANUAL REVIEWS
    # =====================================================

    op.alter_column(
        "manual_reviews",
        "risk_score",
        existing_type=sa.INTEGER(),
        type_=sa.Float(),
        existing_nullable=True,
    )

    op.create_index(
        "ix_manual_reviews_status",
        "manual_reviews",
        ["status"],
        unique=False,
    )

    # =====================================================
    # ORDERS - PAYMENT FIELDS
    # =====================================================

    op.add_column(
        "orders",
        sa.Column(
            "payment_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "payment_approved",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "payment_gate_status",
            sa.String(length=50),
            nullable=True,
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "payment_gate_reason",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "manual_review_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # =====================================================
    # ORDERS - DISCOUNT FIELDS
    # =====================================================

    op.add_column(
        "orders",
        sa.Column(
            "requested_discount_percent",
            sa.Float(),
            nullable=True,
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "approved_discount_percent",
            sa.Float(),
            nullable=True,
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "maximum_safe_discount_percent",
            sa.Float(),
            nullable=True,
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "discount_adjusted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # =====================================================
    # ORDERS - FINAL DECISION FIELDS
    # =====================================================

    op.add_column(
        "orders",
        sa.Column(
            "final_price",
            sa.Float(),
            nullable=True,
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "final_margin_percent",
            sa.Float(),
            nullable=True,
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "decision_explanation",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "final_explanation",
            sa.Text(),
            nullable=True,
        ),
    )

    # =====================================================
    # ORDERS - PROCESSING / AUDIT FIELDS
    # =====================================================

    op.add_column(
        "orders",
        sa.Column(
            "processed_by",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "inventory_deducted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "audit_event_type",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "audit_performed_by",
            sa.String(length=100),
            nullable=True,
        ),
    )

    # =====================================================
    # UPDATED AT
    # =====================================================

    op.add_column(
        "orders",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # =====================================================
    # ORDERS INDEXES
    # =====================================================

    op.create_index(
        "ix_orders_created_at",
        "orders",
        ["created_at"],
        unique=False,
    )

    op.create_index(
        "ix_orders_manual_review_required",
        "orders",
        ["manual_review_required"],
        unique=False,
    )

    op.create_index(
        "ix_orders_status",
        "orders",
        ["status"],
        unique=False,
    )


# =========================================================
# DOWNGRADE
# =========================================================

def downgrade() -> None:

    op.drop_index(
        "ix_orders_status",
        table_name="orders",
    )

    op.drop_index(
        "ix_orders_manual_review_required",
        table_name="orders",
    )

    op.drop_index(
        "ix_orders_created_at",
        table_name="orders",
    )

    op.drop_column(
        "orders",
        "updated_at",
    )

    op.drop_column(
        "orders",
        "audit_performed_by",
    )

    op.drop_column(
        "orders",
        "audit_event_type",
    )

    op.drop_column(
        "orders",
        "inventory_deducted",
    )

    op.drop_column(
        "orders",
        "processed_by",
    )

    op.drop_column(
        "orders",
        "final_explanation",
    )

    op.drop_column(
        "orders",
        "decision_explanation",
    )

    op.drop_column(
        "orders",
        "final_margin_percent",
    )

    op.drop_column(
        "orders",
        "final_price",
    )

    op.drop_column(
        "orders",
        "discount_adjusted",
    )

    op.drop_column(
        "orders",
        "maximum_safe_discount_percent",
    )

    op.drop_column(
        "orders",
        "approved_discount_percent",
    )

    op.drop_column(
        "orders",
        "requested_discount_percent",
    )

    op.drop_column(
        "orders",
        "manual_review_required",
    )

    op.drop_column(
        "orders",
        "payment_gate_reason",
    )

    op.drop_column(
        "orders",
        "payment_gate_status",
    )

    op.drop_column(
        "orders",
        "payment_approved",
    )

    op.drop_column(
        "orders",
        "payment_required",
    )

    op.drop_index(
        "ix_manual_reviews_status",
        table_name="manual_reviews",
    )

    op.alter_column(
        "manual_reviews",
        "risk_score",
        existing_type=sa.Float(),
        type_=sa.INTEGER(),
        existing_nullable=True,
    )

    op.drop_index(
        "ix_audit_logs_risk_level",
        table_name="audit_logs",
    )

    op.drop_index(
        "ix_audit_logs_performed_by",
        table_name="audit_logs",
    )

    op.drop_index(
        "ix_audit_logs_order_id",
        table_name="audit_logs",
    )

    op.drop_index(
        "ix_audit_logs_order_created",
        table_name="audit_logs",
    )

    op.drop_index(
        "ix_audit_logs_old_status",
        table_name="audit_logs",
    )

    op.drop_index(
        "ix_audit_logs_new_status",
        table_name="audit_logs",
    )

    op.drop_index(
        "ix_audit_logs_merchant_id",
        table_name="audit_logs",
    )

    op.drop_index(
        "ix_audit_logs_merchant_created",
        table_name="audit_logs",
    )

    op.drop_index(
        "ix_audit_logs_id",
        table_name="audit_logs",
    )

    op.drop_index(
        "ix_audit_logs_event_type",
        table_name="audit_logs",
    )

    op.drop_index(
        "ix_audit_logs_created_at",
        table_name="audit_logs",
    )

    op.alter_column(
        "audit_logs",
        "created_at",
        existing_type=sa.TIMESTAMP(),
        nullable=True,
        existing_server_default=sa.text(
            "CURRENT_TIMESTAMP"
        ),
    )