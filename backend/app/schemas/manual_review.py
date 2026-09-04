from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


# =========================================================
# MANUAL REVIEW ACTION
# =========================================================

class ManualReviewAction(str, Enum):

    APPROVE = "APPROVE"

    REJECT = "REJECT"


# =========================================================
# MANUAL REVIEW RESPONSE
# =========================================================

class ManualReviewResponse(BaseModel):

    id: int

    order_id: int

    merchant_id: int

    reason: str

    risk_score: Optional[float] = None

    risk_level: Optional[str] = None

    status: str

    reviewed_by: Optional[str] = None

    review_comment: Optional[str] = None

    created_at: datetime

    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =========================================================
# MANUAL REVIEW DECISION
# =========================================================

class ManualReviewDecision(BaseModel):

    action: ManualReviewAction

    reviewed_by: Optional[str] = None

    review_comment: Optional[str] = None