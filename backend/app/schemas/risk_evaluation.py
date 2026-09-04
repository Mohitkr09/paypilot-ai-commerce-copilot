from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# =========================================================
# RISK EVALUATION REQUEST
# =========================================================

class RiskEvaluationRequest(BaseModel):
    order_id: int = Field(
        ...,
        gt=0,
        description="Internal order ID",
    )

    payment_id: Optional[int] = Field(
        default=None,
        gt=0,
        description="Internal payment ID",
    )


# =========================================================
# RISK EVALUATION RESPONSE
# =========================================================

class RiskEvaluationResponse(BaseModel):

    id: int

    order_id: int

    payment_id: Optional[int] = None

    quantity: int

    discount_percent: Decimal

    final_amount: Decimal

    risk_score: int

    risk_level: str

    risk_reason: str

    decision: str

    created_at: Optional[str] = None