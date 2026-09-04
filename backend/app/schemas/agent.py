from typing import Optional

from pydantic import BaseModel, Field


# =========================================================
# AGENT CHAT REQUEST
# =========================================================

class AgentChatRequest(BaseModel):

    merchant_id: int = Field(
        ...,
        description="Merchant ID making the request",
    )

    message: str = Field(
        ...,
        min_length=1,
        description="Natural language request",
    )


# =========================================================
# AGENT CHAT RESPONSE
# =========================================================

class AgentChatResponse(BaseModel):

    # =====================================================
    # BASIC RESPONSE
    # =====================================================

    message: str = Field(
        ...,
        description="AI agent response message",
    )

    intent: Optional[str] = Field(
        default=None,
        description="Detected agent intent",
    )

    merchant_id: int = Field(
        ...,
        description="Merchant ID",
    )

    # =====================================================
    # PRODUCT
    # =====================================================

    product_id: Optional[int] = Field(
        default=None,
        description="Product ID",
    )

    product_name: Optional[str] = Field(
        default=None,
        description="Product name",
    )

    # =====================================================
    # ORDER REQUEST
    # =====================================================

    quantity: Optional[int] = Field(
        default=None,
        description="Requested order quantity",
    )

    requested_discount_percent: Optional[float] = Field(
        default=None,
        description="Discount requested by merchant",
    )

    # =====================================================
    # ORDER AMOUNTS
    # =====================================================

    original_amount: Optional[float] = Field(
        default=None,
        description="Original order amount",
    )

    final_amount: Optional[float] = Field(
        default=None,
        description="Final order amount after discount",
    )

    approved_discount_percent: Optional[float] = Field(
        default=None,
        description="Discount approved by PayPilot",
    )

    # =====================================================
    # RISK
    # =====================================================

    risk_score: Optional[float] = Field(
        default=None,
        description="Calculated risk score",
    )

    risk_level: Optional[str] = Field(
        default=None,
        description="Risk level: LOW, MEDIUM, HIGH, CRITICAL",
    )

    # =====================================================
    # ORDER RESULT
    # =====================================================

    order_id: Optional[int] = Field(
        default=None,
        description="Created order ID",
    )

    order_status: Optional[str] = Field(
        default=None,
        description="Final order status",
    )

    # =====================================================
    # MANUAL REVIEW
    # =====================================================

    manual_review_required: bool = Field(
        default=False,
        description="Whether manual review is required",
    )