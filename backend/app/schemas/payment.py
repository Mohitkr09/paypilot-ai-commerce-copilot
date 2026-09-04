from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# =========================================================
# CREATE PAYMENT
# =========================================================

class PaymentCreate(BaseModel):

    order_id: int = Field(
        ...,
        gt=0,
    )

    currency: str = Field(
        default="INR",
        min_length=3,
        max_length=10,
    )


# =========================================================
# VERIFY RAZORPAY PAYMENT
# =========================================================

class PaymentVerify(BaseModel):

    razorpay_order_id: str = Field(
        ...,
        min_length=1,
    )

    razorpay_payment_id: str = Field(
        ...,
        min_length=1,
    )

    razorpay_signature: str = Field(
        ...,
        min_length=1,
    )

    payment_method: Optional[str] = None


# =========================================================
# PAYMENT RESPONSE
# =========================================================

class PaymentResponse(BaseModel):

    id: int

    order_id: int

    merchant_id: int

    amount: float

    currency: str

    status: str

    razorpay_order_id: Optional[str] = None

    razorpay_payment_id: Optional[str] = None

    razorpay_signature: Optional[str] = None

    failure_reason: Optional[str] = None

    payment_method: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True
    )