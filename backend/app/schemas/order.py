from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


# =========================================================
# CREATE ORDER
# =========================================================

class OrderCreate(BaseModel):
    merchant_id: int
    product_id: int
    quantity: int = Field(gt=0)

    requested_discount_percent: float = Field(
        ge=0,
        le=100,
    )


# =========================================================
# ORDER RESPONSE
# =========================================================

class OrderResponse(BaseModel):

    # =====================================================
    # BASIC ORDER INFORMATION
    # =====================================================

    id: int

    merchant_id: int
    product_id: int
    quantity: int

    original_amount: float

    discount_percent: float
    discount_amount: float
    final_amount: float

    status: str

    # =====================================================
    # AI RISK INFORMATION
    # =====================================================

    risk_score: Optional[float] = None

    risk_level: Optional[str] = None

    risk_reason: Optional[str] = None

    risk_factors: Optional[str] = None

    ai_explanation: Optional[str] = None

    # =====================================================
    # HUMAN-IN-THE-LOOP
    # =====================================================

    manual_review_required: bool = False

    # =====================================================
    # PAYMENT GATE
    # =====================================================

    payment_approved: bool = False

    # =====================================================
    # INVENTORY
    # =====================================================

    inventory_deducted: bool = False

    # =====================================================
    # ORDER TIMESTAMPS
    # =====================================================

    created_at: Optional[datetime] = None

    updated_at: Optional[datetime] = None

    # =====================================================
    # PYDANTIC CONFIG
    # =====================================================

    class Config:
        from_attributes = True