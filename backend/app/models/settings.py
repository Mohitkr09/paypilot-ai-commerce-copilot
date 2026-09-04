from sqlalchemy import Boolean, Column, Float, Integer

from app.db.database import Base


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)

    # General
    risk_engine_enabled = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Risk thresholds
    low_risk_threshold = Column(
        Float,
        default=30,
        nullable=False,
    )

    high_risk_threshold = Column(
        Float,
        default=70,
        nullable=False,
    )

    # Manual review
    manual_review_enabled = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    manual_review_threshold = Column(
        Float,
        default=50,
        nullable=False,
    )

    # Discount rules
    max_discount = Column(
        Float,
        default=30,
        nullable=False,
    )

    require_review_discount = Column(
        Float,
        default=20,
        nullable=False,
    )