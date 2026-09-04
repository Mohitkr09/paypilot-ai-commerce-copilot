from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    ForeignKey,
    Text,
    JSON,
)

from sqlalchemy.sql import func

from app.db.database import Base


class Payment(Base):

    __tablename__ = "payments"

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
        ForeignKey("orders.id"),
        nullable=False,
        index=True,
    )

    # =========================================================
    # MERCHANT
    # =========================================================

    merchant_id = Column(
        Integer,
        ForeignKey("merchants.id"),
        nullable=False,
        index=True,
    )

    # =========================================================
    # PAYMENT AMOUNT
    # =========================================================

    amount = Column(
        Numeric(12, 2),
        nullable=False,
    )

    currency = Column(
        String(10),
        nullable=False,
        default="INR",
    )

    # =========================================================
    # PAYMENT STATUS
    # =========================================================
    #
    # CREATED
    # PENDING
    # AUTHORIZED
    # CAPTURED
    # FAILED
    # REFUNDED
    # CANCELLED
    #
    # =========================================================

    status = Column(
        String(30),
        nullable=False,
        default="CREATED",
        index=True,
    )

    # =========================================================
    # RAZORPAY ORDER
    # =========================================================

    razorpay_order_id = Column(
        String(100),
        nullable=True,
        unique=True,
        index=True,
    )

    # =========================================================
    # RAZORPAY PAYMENT
    # =========================================================

    razorpay_payment_id = Column(
        String(100),
        nullable=True,
        unique=True,
        index=True,
    )

    # =========================================================
    # RAZORPAY SIGNATURE
    # =========================================================

    razorpay_signature = Column(
        String(255),
        nullable=True,
    )

    # =========================================================
    # ACTUAL PAYMENT METHOD
    # =========================================================
    #
    # This is populated after Razorpay verification.
    #
    # Examples:
    #
    #   upi
    #   card
    #   netbanking
    #   wallet
    #   emi
    #   paylater
    #
    # The Razorpay response is authoritative.
    #
    # =========================================================

    payment_method = Column(
        String(50),
        nullable=True,
        index=True,
    )

    # =========================================================
    # PAYMENT METHOD DETAILS
    # =========================================================
    #
    # Optional structured information returned by Razorpay.
    #
    # Examples:
    #
    # {
    #     "card": {
    #         "network": "Visa",
    #         "type": "credit",
    #         "last4": "1234"
    #     }
    # }
    #
    # {
    #     "bank": "HDFC"
    # }
    #
    # {
    #     "wallet": "paytm"
    # }
    #
    # Never store:
    # - CVV
    # - full card number
    # - UPI PIN
    # - passwords
    # - other sensitive credentials
    #
    # =========================================================

    payment_method_details = Column(
        JSON,
        nullable=True,
    )

    # =========================================================
    # FAILURE INFORMATION
    # =========================================================

    failure_reason = Column(
        Text,
        nullable=True,
    )

    # =========================================================
    # TIMESTAMPS
    # =========================================================

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # =========================================================
    # DEBUG REPRESENTATION
    # =========================================================

    def __repr__(self):

        return (
            f"<Payment("
            f"id={self.id}, "
            f"order_id={self.order_id}, "
            f"merchant_id={self.merchant_id}, "
            f"amount={self.amount}, "
            f"currency='{self.currency}', "
            f"status='{self.status}', "
            f"payment_method='{self.payment_method}', "
            f"razorpay_order_id='{self.razorpay_order_id}', "
            f"razorpay_payment_id='{self.razorpay_payment_id}'"
            f")>"
        )