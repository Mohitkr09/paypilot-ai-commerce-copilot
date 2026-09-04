from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, Numeric, String, Text, Index

from app.db.database import Base


class Campaign(Base):
    """
    Phase 1 Campaign Orchestrator proposal.

    IMPORTANT:
    - A campaign created here is only a proposal.
    - It is never activated by the AI.
    - Policy/margin validation is Phase 2.
    - Merchant approval/activation is Phase 3.
    """

    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, nullable=False, index=True)

    name = Column(String(160), nullable=False)
    objective = Column(String(120), nullable=False)
    brief = Column(Text, nullable=False)

    strategy_type = Column(String(50), nullable=False, default="GROWTH")
    status = Column(String(40), nullable=False, default="DRAFT", index=True)

    suggested_discount_percent = Column(Numeric(10, 2), nullable=False, default=0)

    # IDs of products selected by the proposal engine.
    product_ids = Column(JSON, nullable=False, default=list)

    # Human-readable proposed actions. Nothing in this field is executed.
    proposed_actions = Column(JSON, nullable=False, default=list)

    # Explicit governance metadata for the proposal.
    governance = Column(JSON, nullable=False, default=dict)

    explanation = Column(Text, nullable=False, default="")

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        Index("ix_campaigns_merchant_status", "merchant_id", "status"),
    )
