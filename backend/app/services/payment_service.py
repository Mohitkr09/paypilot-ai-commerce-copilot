from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.models.order import Order

from app.services.razorpay_service import RazorpayService
from app.services.order_service import OrderService
from app.services.audit_log_service import AuditLogService


class PaymentService:

    # =========================================================
    # INTERNAL HELPERS
    # =========================================================

    @staticmethod
    def _normalize_currency(
        currency: str = "INR",
    ) -> str:

        currency = (
            currency or "INR"
        ).strip().upper()

        if len(currency) != 3:
            raise ValueError(
                "Currency must be a valid 3-letter code"
            )

        return currency

    # =========================================================
    # DECIMAL AMOUNT
    # =========================================================

    @staticmethod
    def _decimal_amount(amount) -> Decimal:

        try:
            value = (
                Decimal(str(amount))
                .quantize(
                    Decimal("0.01")
                )
            )

        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ):
            raise ValueError(
                "Invalid payment amount"
            )

        if value <= 0:
            raise ValueError(
                "Payment amount must be greater than zero"
            )

        return value

    # =========================================================
    # SMALLEST CURRENCY UNIT
    # =========================================================

    @staticmethod
    def _amount_in_smallest_unit(amount) -> int:

        decimal_amount = (
            PaymentService._decimal_amount(
                amount
            )
        )

        return int(
            decimal_amount * 100
        )

    # =========================================================
    # PAYMENT APPROVAL CHECK
    # =========================================================

    @staticmethod
    def _is_payment_approved(
        order: Order,
    ) -> bool:

        if order is None:
            return False

        if order.status != "APPROVED":
            return False

        payment_approved = getattr(
            order,
            "payment_approved",
            None,
        )

        if payment_approved is True:
            return True

        if payment_approved is False:

            risk_level = str(
                getattr(
                    order,
                    "risk_level",
                    "",
                )
                or ""
            ).upper()

            return risk_level in (
                "LOW",
                "MEDIUM",
            )

        risk_level = str(
            getattr(
                order,
                "risk_level",
                "",
            )
            or ""
        ).upper()

        return risk_level != "HIGH"

    # =========================================================
    # CREATE INTERNAL PAYMENT
    #
    # IMPORTANT:
    # This method is idempotent per order.
    #
    # Payment.order_id MUST be UNIQUE at DB level.
    # =========================================================

    @staticmethod
    def create_payment(
        db: Session,
        order: Order,
        currency: str = "INR",
    ) -> Payment:

        if order is None:
            raise ValueError(
                "Order is required"
            )

        if order.id is None:
            raise ValueError(
                "Order must be saved before creating payment"
            )

        if order.status != "APPROVED":
            raise ValueError(
                "Payment can only be created "
                "for an APPROVED order"
            )

        if not PaymentService._is_payment_approved(order):
            raise ValueError(
                "Order was not approved by "
                "the PayPilot payment gate"
            )

        currency = (
            PaymentService._normalize_currency(
                currency
            )
        )

        amount = (
            PaymentService._decimal_amount(
                order.final_amount
            )
        )

        # -----------------------------------------------------
        # LOCK EXISTING PAYMENT
        # -----------------------------------------------------

        existing_payment = (
            db.query(Payment)
            .filter(
                Payment.order_id == order.id
            )
            .with_for_update()
            .first()
        )

        if existing_payment:

            existing_amount = (
                PaymentService._decimal_amount(
                    existing_payment.amount
                )
            )

            if existing_amount != amount:
                raise ValueError(
                    "Existing payment amount does not "
                    "match order amount"
                )

            existing_currency = str(
                existing_payment.currency or ""
            ).upper()

            if existing_currency != currency:
                raise ValueError(
                    "Existing payment currency does not "
                    "match requested currency"
                )

            # -------------------------------------------------
            # IDEMPOTENCY
            #
            # If payment already exists, NEVER create another
            # Payment row for this order.
            # -------------------------------------------------

            return existing_payment

        # -----------------------------------------------------
        # CREATE PAYMENT
        # -----------------------------------------------------

        payment = Payment(
            order_id=order.id,
            merchant_id=order.merchant_id,
            amount=amount,
            currency=currency,
            status="CREATED",
        )

        db.add(payment)

        db.flush()

        # -----------------------------------------------------
        # AUDIT
        # -----------------------------------------------------

        AuditLogService.log_payment_event(
            db=db,
            merchant_id=payment.merchant_id,
            order_id=payment.order_id,
            payment_id=payment.id,
            event_type="PAYMENT_CREATED",
            message=(
                f"Payment {payment.id} created "
                f"for order {payment.order_id}. "
                f"Amount: {payment.amount} "
                f"{payment.currency}"
            ),
            old_status=None,
            new_status="CREATED",
            performed_by="PAYPILOT_PAYMENT_SYSTEM",
            commit=False,
        )

        return payment

    # =========================================================
    # CREATE RAZORPAY ORDER
    #
    # IMPORTANT:
    # Lock payment before checking razorpay_order_id.
    #
    # This prevents:
    #
    # request A -> create Razorpay order
    # request B -> create another Razorpay order
    #
    # =========================================================

    @staticmethod
    def create_razorpay_order(
        db: Session,
        payment: Payment,
    ) -> Payment:

        if payment is None:
            raise ValueError(
                "Payment is required"
            )

        if payment.id is None:
            raise ValueError(
                "Payment must be saved first"
            )

        # -----------------------------------------------------
        # RELOAD + LOCK PAYMENT
        # -----------------------------------------------------

        locked_payment = (
            db.query(Payment)
            .filter(
                Payment.id == payment.id
            )
            .with_for_update()
            .first()
        )

        if not locked_payment:
            raise ValueError(
                "Payment not found"
            )

        payment = locked_payment

        # -----------------------------------------------------
        # ALREADY CAPTURED
        # -----------------------------------------------------

        if payment.status == "CAPTURED":
            return payment

        # -----------------------------------------------------
        # EXISTING RAZORPAY ORDER
        # -----------------------------------------------------

        if payment.razorpay_order_id:

            if payment.status == "CREATED":

                old_status = payment.status

                payment.status = "PENDING"
                payment.failure_reason = None

                db.flush()

                AuditLogService.log_payment_event(
                    db=db,
                    merchant_id=payment.merchant_id,
                    order_id=payment.order_id,
                    payment_id=payment.id,
                    event_type="PAYMENT_PENDING",
                    message=(
                        f"Payment {payment.id} "
                        f"moved to PENDING"
                    ),
                    old_status=old_status,
                    new_status="PENDING",
                    performed_by="PAYPILOT_PAYMENT_SYSTEM",
                    commit=False,
                )

            return payment

        # -----------------------------------------------------
        # TERMINAL STATES
        # -----------------------------------------------------

        if payment.status == "REFUNDED":
            raise ValueError(
                "Refunded payment cannot be initialized"
            )

        if payment.status == "CANCELLED":
            raise ValueError(
                "Cancelled payment cannot be initialized"
            )

        # -----------------------------------------------------
        # AMOUNT
        # -----------------------------------------------------

        amount = (
            PaymentService._decimal_amount(
                payment.amount
            )
        )

        # -----------------------------------------------------
        # CURRENCY
        # -----------------------------------------------------

        currency = (
            PaymentService._normalize_currency(
                payment.currency
            )
        )

        payment.currency = currency

        old_status = payment.status

        # -----------------------------------------------------
        # CREATE RAZORPAY ORDER
        # -----------------------------------------------------

        try:

            razorpay_order = (
                RazorpayService.create_order(
                    amount=amount,
                    currency=currency,
                    receipt=f"payment_{payment.id}",
                    notes={
                        "payment_id": str(
                            payment.id
                        ),
                        "order_id": str(
                            payment.order_id
                        ),
                        "merchant_id": str(
                            payment.merchant_id
                        ),
                    },
                )
            )

        except Exception as e:

            payment.failure_reason = str(e)

            db.flush()

            AuditLogService.log_payment_event(
                db=db,
                merchant_id=payment.merchant_id,
                order_id=payment.order_id,
                payment_id=payment.id,
                event_type="RAZORPAY_ORDER_FAILED",
                message=(
                    f"Unable to create Razorpay order "
                    f"for payment {payment.id}: {str(e)}"
                ),
                old_status=old_status,
                new_status=old_status,
                performed_by="PAYPILOT_PAYMENT_SYSTEM",
                commit=False,
            )

            raise HTTPException(
                status_code=502,
                detail={
                    "message": (
                        "Unable to create "
                        "Razorpay order"
                    ),
                    "error": str(e),
                },
            )

        if not razorpay_order:
            raise RuntimeError(
                "Razorpay returned empty order response"
            )

        razorpay_order_id = (
            razorpay_order.get("id")
        )

        if not razorpay_order_id:
            raise RuntimeError(
                "Razorpay did not return an order ID"
            )

        # -----------------------------------------------------
        # VERIFY AMOUNT
        # -----------------------------------------------------

        expected_amount = (
            PaymentService
            ._amount_in_smallest_unit(
                amount
            )
        )

        try:
            returned_amount = int(
                razorpay_order.get(
                    "amount",
                    0,
                )
            )
        except (
            ValueError,
            TypeError,
        ):
            returned_amount = 0

        if returned_amount != expected_amount:
            raise RuntimeError(
                "Razorpay order amount does not "
                "match internal payment amount"
            )

        # -----------------------------------------------------
        # VERIFY CURRENCY
        # -----------------------------------------------------

        returned_currency = str(
            razorpay_order.get(
                "currency",
                "",
            )
        ).upper()

        if returned_currency != currency:
            raise RuntimeError(
                "Razorpay order currency does not "
                "match internal payment currency"
            )

        # -----------------------------------------------------
        # SAVE RAZORPAY ORDER
        # -----------------------------------------------------

        payment.razorpay_order_id = (
            razorpay_order_id
        )

        payment.status = "PENDING"
        payment.failure_reason = None

        db.flush()

        AuditLogService.log_payment_event(
            db=db,
            merchant_id=payment.merchant_id,
            order_id=payment.order_id,
            payment_id=payment.id,
            event_type="RAZORPAY_ORDER_CREATED",
            message=(
                f"Razorpay order "
                f"{razorpay_order_id} created "
                f"for payment {payment.id}"
            ),
            old_status=old_status,
            new_status="PENDING",
            performed_by="PAYPILOT_PAYMENT_SYSTEM",
            commit=False,
        )

        return payment

    # =========================================================
    # GET PAYMENT
    # =========================================================

    @staticmethod
    def get_payment(
        db: Session,
        payment_id: int,
    ) -> Optional[Payment]:

        return (
            db.query(Payment)
            .filter(
                Payment.id == payment_id
            )
            .first()
        )

    # =========================================================
    # GET PAYMENT BY ORDER
    # =========================================================

    @staticmethod
    def get_payment_by_order(
        db: Session,
        order_id: int,
    ) -> Optional[Payment]:

        return (
            db.query(Payment)
            .filter(
                Payment.order_id == order_id
            )
            .first()
        )

    # =========================================================
    # GET PAYMENT BY RAZORPAY ORDER
    # =========================================================

    @staticmethod
    def get_payment_by_razorpay_order(
        db: Session,
        razorpay_order_id: str,
    ) -> Optional[Payment]:

        if not razorpay_order_id:
            return None

        return (
            db.query(Payment)
            .filter(
                Payment.razorpay_order_id
                == razorpay_order_id
            )
            .with_for_update()
            .first()
        )

    # =========================================================
    # MARK PAYMENT PENDING
    # =========================================================

    @staticmethod
    def mark_pending(
        db: Session,
        payment: Payment,
    ) -> Payment:

        if payment is None:
            raise ValueError(
                "Payment is required"
            )

        if payment.status in (
            "CAPTURED",
            "REFUNDED",
            "CANCELLED",
        ):
            raise ValueError(
                "Payment cannot be marked PENDING "
                f"from status {payment.status}"
            )

        old_status = payment.status

        if old_status == "PENDING":
            return payment

        payment.status = "PENDING"
        payment.failure_reason = None

        db.flush()

        AuditLogService.log_payment_event(
            db=db,
            merchant_id=payment.merchant_id,
            order_id=payment.order_id,
            payment_id=payment.id,
            event_type="PAYMENT_PENDING",
            message=(
                f"Payment {payment.id} moved to PENDING"
            ),
            old_status=old_status,
            new_status="PENDING",
            performed_by="PAYPILOT_PAYMENT_SYSTEM",
            commit=False,
        )

        return payment

    # =========================================================
    # AUTHORIZE PAYMENT
    # =========================================================

    @staticmethod
    def authorize_payment(
        db: Session,
        payment: Payment,
        razorpay_order_id: Optional[str] = None,
    ) -> Payment:

        if payment is None:
            raise ValueError(
                "Payment is required"
            )

        if payment.status in (
            "CAPTURED",
            "REFUNDED",
            "CANCELLED",
        ):
            raise ValueError(
                "Payment cannot be authorized "
                f"from status {payment.status}"
            )

        old_status = payment.status

        if razorpay_order_id:

            if (
                payment.razorpay_order_id
                and payment.razorpay_order_id
                != razorpay_order_id
            ):
                raise ValueError(
                    "Razorpay order ID mismatch"
                )

            payment.razorpay_order_id = (
                razorpay_order_id
            )

        # -----------------------------------------------------
        # IDEMPOTENCY
        # -----------------------------------------------------

        if old_status == "AUTHORIZED":
            return payment

        payment.status = "AUTHORIZED"
        payment.failure_reason = None

        db.flush()

        AuditLogService.log_payment_event(
            db=db,
            merchant_id=payment.merchant_id,
            order_id=payment.order_id,
            payment_id=payment.id,
            event_type="PAYMENT_AUTHORIZED",
            message=(
                f"Payment {payment.id} authorized"
            ),
            old_status=old_status,
            new_status="AUTHORIZED",
            performed_by="RAZORPAY",
            commit=False,
        )

        return payment

    # =========================================================
    # CAPTURE PAYMENT
    #
    # CENTRAL IDEMPOTENT CAPTURE METHOD
    #
    # Both /verify and webhook should eventually use this.
    # =========================================================

    @staticmethod
    def capture_payment(
        db: Session,
        payment: Payment,
        razorpay_payment_id: Optional[str] = None,
        razorpay_signature: Optional[str] = None,
        payment_method: Optional[str] = None,
    ) -> Payment:

        if payment is None:
            raise ValueError(
                "Payment is required"
            )

        # -----------------------------------------------------
        # LOCK PAYMENT
        # -----------------------------------------------------

        locked_payment = (
            db.query(Payment)
            .filter(
                Payment.id == payment.id
            )
            .with_for_update()
            .first()
        )

        if not locked_payment:
            raise ValueError(
                "Payment not found"
            )

        payment = locked_payment

        # -----------------------------------------------------
        # TERMINAL STATES
        # -----------------------------------------------------

        if payment.status == "REFUNDED":
            raise ValueError(
                "Refunded payment cannot be captured"
            )

        if payment.status == "CANCELLED":
            raise ValueError(
                "Cancelled payment cannot be captured"
            )

        # -----------------------------------------------------
        # IDEMPOTENCY
        #
        # Second webhook / second /verify:
        #
        # CAPTURED -> return existing payment
        #
        # BUT if another Razorpay payment ID is supplied,
        # reject it instead of silently overwriting data.
        # -----------------------------------------------------

        if payment.status == "CAPTURED":

            if (
                razorpay_payment_id
                and payment.razorpay_payment_id
                and payment.razorpay_payment_id
                != razorpay_payment_id
            ):
                raise ValueError(
                    "Different Razorpay payment ID "
                    "cannot be applied to an already "
                    "captured payment"
                )

            if (
                razorpay_payment_id
                and not payment.razorpay_payment_id
            ):
                payment.razorpay_payment_id = (
                    razorpay_payment_id
                )

            if (
                razorpay_signature
                and not payment.razorpay_signature
            ):
                payment.razorpay_signature = (
                    razorpay_signature
                )

            if (
                payment_method
                and not payment.payment_method
            ):
                payment.payment_method = (
                    payment_method
                )

            db.flush()

            return payment

        # -----------------------------------------------------
        # SAVE RAZORPAY PAYMENT ID
        # -----------------------------------------------------

        if razorpay_payment_id:

            if (
                payment.razorpay_payment_id
                and payment.razorpay_payment_id
                != razorpay_payment_id
            ):
                raise ValueError(
                    "Razorpay payment ID does not "
                    "match existing payment"
                )

            payment.razorpay_payment_id = (
                razorpay_payment_id
            )

        if razorpay_signature:
            payment.razorpay_signature = (
                razorpay_signature
            )

        if payment_method:
            payment.payment_method = (
                payment_method
            )

        old_status = payment.status

        # -----------------------------------------------------
        # CAPTURE
        # -----------------------------------------------------

        payment.status = "CAPTURED"
        payment.failure_reason = None

        db.flush()

        # -----------------------------------------------------
        # ONE CAPTURE AUDIT EVENT
        # -----------------------------------------------------

        AuditLogService.log_payment_event(
            db=db,
            merchant_id=payment.merchant_id,
            order_id=payment.order_id,
            payment_id=payment.id,
            event_type="PAYMENT_CAPTURED",
            message=(
                f"Payment {payment.id} captured successfully"
            ),
            old_status=old_status,
            new_status="CAPTURED",
            performed_by="RAZORPAY",
            commit=False,
        )

        return payment

    # =========================================================
    # MARK ORDER PAID
    #
    # This is also made idempotent at the PaymentService level.
    # =========================================================

    @staticmethod
    def _mark_order_paid(
        db: Session,
        payment: Payment,
    ) -> None:

        try:

            OrderService.mark_payment_captured(
                db=db,
                order_id=payment.order_id,
                payment_id=payment.id,
            )

        except HTTPException:
            raise

        except Exception as e:

            raise HTTPException(
                status_code=409,
                detail={
                    "message": (
                        "Payment was captured but "
                        "order could not be marked paid"
                    ),
                    "error": str(e),
                },
            )

    # =========================================================
    # FAIL PAYMENT
    # =========================================================

    @staticmethod
    def fail_payment(
        db: Session,
        payment: Payment,
        failure_reason: str,
    ) -> Payment:

        if payment is None:
            raise ValueError(
                "Payment is required"
            )

        # -----------------------------------------------------
        # LOCK
        # -----------------------------------------------------

        locked_payment = (
            db.query(Payment)
            .filter(
                Payment.id == payment.id
            )
            .with_for_update()
            .first()
        )

        if not locked_payment:
            raise ValueError(
                "Payment not found"
            )

        payment = locked_payment

        if payment.status == "CAPTURED":
            raise ValueError(
                "Captured payment cannot be marked failed"
            )

        if payment.status == "REFUNDED":
            raise ValueError(
                "Refunded payment cannot be marked failed"
            )

        if payment.status == "CANCELLED":
            raise ValueError(
                "Cancelled payment cannot be marked failed"
            )

        # -----------------------------------------------------
        # IDEMPOTENCY
        # -----------------------------------------------------

        if payment.status == "FAILED":
            return payment

        old_status = payment.status

        payment.status = "FAILED"

        payment.failure_reason = (
            failure_reason
            or "Payment failed"
        )

        db.flush()

        AuditLogService.log_payment_event(
            db=db,
            merchant_id=payment.merchant_id,
            order_id=payment.order_id,
            payment_id=payment.id,
            event_type="PAYMENT_FAILED",
            message=(
                f"Payment {payment.id} failed: "
                f"{payment.failure_reason}"
            ),
            old_status=old_status,
            new_status="FAILED",
            performed_by="RAZORPAY",
            commit=False,
        )

        return payment

    # =========================================================
    # VERIFY + CAPTURE PAYMENT
    #
    # /verify is now idempotent.
    # =========================================================

    @staticmethod
    def verify_and_capture(
        db: Session,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> Payment:

        if not razorpay_order_id:
            raise HTTPException(
                status_code=400,
                detail="Razorpay order ID is required",
            )

        if not razorpay_payment_id:
            raise HTTPException(
                status_code=400,
                detail="Razorpay payment ID is required",
            )

        if not razorpay_signature:
            raise HTTPException(
                status_code=400,
                detail="Razorpay signature is required",
            )

        # -----------------------------------------------------
        # GET + LOCK
        # -----------------------------------------------------

        payment = (
            PaymentService
            .get_payment_by_razorpay_order(
                db=db,
                razorpay_order_id=razorpay_order_id,
            )
        )

        if not payment:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Internal payment not found "
                    "for Razorpay order"
                ),
            )

        # -----------------------------------------------------
        # ALREADY CAPTURED
        #
        # This is the important second-/verify case.
        # -----------------------------------------------------

        if payment.status == "CAPTURED":

            if (
                payment.razorpay_payment_id
                and payment.razorpay_payment_id
                != razorpay_payment_id
            ):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Payment is already captured "
                        "with a different Razorpay "
                        "payment ID"
                    ),
                )

            return payment

        if payment.status == "REFUNDED":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Refunded payment cannot be verified"
                ),
            )

        if payment.status == "CANCELLED":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Cancelled payment cannot be verified"
                ),
            )

        # -----------------------------------------------------
        # VERIFY ORDER ID
        # -----------------------------------------------------

        if (
            payment.razorpay_order_id
            != razorpay_order_id
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Razorpay order ID does not "
                    "match internal payment"
                ),
            )

        # -----------------------------------------------------
        # VERIFY PAYMENT SIGNATURE
        # -----------------------------------------------------

        try:

            try:

                signature_valid = (
                    RazorpayService.verify_payment(
                        razorpay_order_id=(
                            razorpay_order_id
                        ),
                        razorpay_payment_id=(
                            razorpay_payment_id
                        ),
                        razorpay_signature=(
                            razorpay_signature
                        ),
                    )
                )

            except AttributeError:

                signature_valid = (
                    RazorpayService
                    .verify_payment_signature(
                        razorpay_order_id=(
                            razorpay_order_id
                        ),
                        razorpay_payment_id=(
                            razorpay_payment_id
                        ),
                        razorpay_signature=(
                            razorpay_signature
                        ),
                    )
                )

        except Exception as e:

            AuditLogService.log_payment_event(
                db=db,
                merchant_id=payment.merchant_id,
                order_id=payment.order_id,
                payment_id=payment.id,
                event_type="PAYMENT_VERIFICATION_FAILED",
                message=(
                    f"Payment {payment.id} signature "
                    f"verification failed: {str(e)}"
                ),
                old_status=payment.status,
                new_status=payment.status,
                performed_by="PAYPILOT_PAYMENT_SYSTEM",
                commit=False,
            )

            db.commit()

            raise HTTPException(
                status_code=400,
                detail={
                    "message": (
                        "Payment signature "
                        "verification failed"
                    ),
                    "error": str(e),
                },
            )

        if not signature_valid:

            PaymentService.fail_payment(
                db=db,
                payment=payment,
                failure_reason=(
                    "Invalid Razorpay payment signature"
                ),
            )

            db.commit()

            raise HTTPException(
                status_code=400,
                detail="Invalid payment signature",
            )

        # -----------------------------------------------------
        # FETCH PAYMENT FROM RAZORPAY
        # -----------------------------------------------------

        try:

            razorpay_payment = (
                RazorpayService.get_payment(
                    razorpay_payment_id
                )
            )

        except Exception as e:

            raise HTTPException(
                status_code=502,
                detail={
                    "message": (
                        "Unable to verify payment "
                        "with Razorpay"
                    ),
                    "error": str(e),
                },
            )

        if not razorpay_payment:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Razorpay returned empty "
                    "payment information"
                ),
            )

        # -----------------------------------------------------
        # VERIFY PAYMENT ID
        # -----------------------------------------------------

        returned_payment_id = str(
            razorpay_payment.get(
                "id",
                "",
            )
        )

        if returned_payment_id != razorpay_payment_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Razorpay payment ID does not "
                    "match payment response"
                ),
            )

        # -----------------------------------------------------
        # VERIFY ORDER ID
        # -----------------------------------------------------

        returned_order_id = str(
            razorpay_payment.get(
                "order_id",
                "",
            )
        )

        if returned_order_id != razorpay_order_id:

            PaymentService.fail_payment(
                db=db,
                payment=payment,
                failure_reason=(
                    "Razorpay payment belongs "
                    "to a different order"
                ),
            )

            db.commit()

            raise HTTPException(
                status_code=400,
                detail=(
                    "Payment does not belong "
                    "to this Razorpay order"
                ),
            )

        # -----------------------------------------------------
        # VERIFY AMOUNT
        # -----------------------------------------------------

        expected_amount = (
            PaymentService
            ._amount_in_smallest_unit(
                payment.amount
            )
        )

        try:

            returned_amount = int(
                razorpay_payment.get(
                    "amount",
                    0,
                )
            )

        except (
            ValueError,
            TypeError,
        ):

            returned_amount = 0

        if returned_amount != expected_amount:

            PaymentService.fail_payment(
                db=db,
                payment=payment,
                failure_reason=(
                    "Payment amount does not "
                    "match order amount"
                ),
            )

            db.commit()

            raise HTTPException(
                status_code=400,
                detail=(
                    "Payment amount does not "
                    "match order amount"
                ),
            )

        # -----------------------------------------------------
        # VERIFY CURRENCY
        # -----------------------------------------------------

        returned_currency = str(
            razorpay_payment.get(
                "currency",
                "",
            )
        ).upper()

        expected_currency = str(
            payment.currency or "INR"
        ).upper()

        if returned_currency != expected_currency:

            PaymentService.fail_payment(
                db=db,
                payment=payment,
                failure_reason=(
                    "Payment currency does not "
                    "match order currency"
                ),
            )

            db.commit()

            raise HTTPException(
                status_code=400,
                detail=(
                    "Payment currency does not "
                    "match order currency"
                ),
            )

        # -----------------------------------------------------
        # RAZORPAY STATUS
        # -----------------------------------------------------

        razorpay_status = str(
            razorpay_payment.get(
                "status",
                "",
            )
        ).upper()

        # -----------------------------------------------------
        # AUTHORIZED
        # -----------------------------------------------------

        if razorpay_status == "AUTHORIZED":

            PaymentService.authorize_payment(
                db=db,
                payment=payment,
                razorpay_order_id=(
                    razorpay_order_id
                ),
            )

            payment.razorpay_payment_id = (
                razorpay_payment_id
            )

            payment.razorpay_signature = (
                razorpay_signature
            )

            db.commit()

            raise HTTPException(
                status_code=409,
                detail=(
                    "Payment is authorized but "
                    "not captured yet"
                ),
            )

        # -----------------------------------------------------
        # FAILED
        # -----------------------------------------------------

        if razorpay_status == "FAILED":

            reason = (
                razorpay_payment.get(
                    "error_description"
                )
                or razorpay_payment.get(
                    "error_reason"
                )
                or "Razorpay payment failed"
            )

            reason = str(reason)

            PaymentService.fail_payment(
                db=db,
                payment=payment,
                failure_reason=reason,
            )

            try:

                OrderService.mark_payment_failed(
                    db=db,
                    order_id=payment.order_id,
                    reason=reason,
                    payment_id=payment.id,
                )

            except Exception as e:

                db.rollback()

                raise HTTPException(
                    status_code=500,
                    detail={
                        "message": (
                            "Payment failed but "
                            "order status could not "
                            "be updated"
                        ),
                        "error": str(e),
                    },
                )

            db.commit()

            raise HTTPException(
                status_code=400,
                detail=reason,
            )

        # -----------------------------------------------------
        # MUST BE CAPTURED
        # -----------------------------------------------------

        if razorpay_status != "CAPTURED":

            raise HTTPException(
                status_code=409,
                detail=(
                    "Payment is not captured. "
                    f"Current Razorpay status: "
                    f"{razorpay_status or 'UNKNOWN'}"
                ),
            )

        # -----------------------------------------------------
        # PAYMENT METHOD
        # -----------------------------------------------------

        payment_method = (
            razorpay_payment.get("method")
        )

        # -----------------------------------------------------
        # CAPTURE INTERNAL PAYMENT
        # -----------------------------------------------------

        payment = (
            PaymentService.capture_payment(
                db=db,
                payment=payment,
                razorpay_payment_id=(
                    razorpay_payment_id
                ),
                razorpay_signature=(
                    razorpay_signature
                ),
                payment_method=payment_method,
            )
        )

        # -----------------------------------------------------
        # MARK ORDER PAID
        # -----------------------------------------------------

        try:

            PaymentService._mark_order_paid(
                db=db,
                payment=payment,
            )

        except HTTPException:

            db.rollback()
            raise

        # -----------------------------------------------------
        # COMMIT EVERYTHING
        # -----------------------------------------------------

        db.commit()

        db.refresh(payment)

        return payment

    # =========================================================
    # WEBHOOK: PAYMENT CAPTURED
    #
    # IMPORTANT:
    # Webhook signature should be verified BEFORE this method
    # is called.
    #
    # This method is intentionally idempotent.
    #
    # WEBHOOK BEFORE /verify:
    #
    #     webhook -> CAPTURED
    #     /verify  -> sees CAPTURED -> returns
    #
    # WEBHOOK AFTER /verify:
    #
    #     /verify  -> CAPTURED
    #     webhook  -> sees CAPTURED -> returns
    #
    # =========================================================

    @staticmethod
    def handle_webhook_payment_captured(
        db: Session,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        amount: int,
        currency: str,
        payment_method: Optional[str] = None,
    ) -> Payment:

        if not razorpay_order_id:
            raise ValueError(
                "Webhook Razorpay order ID is required"
            )

        if not razorpay_payment_id:
            raise ValueError(
                "Webhook Razorpay payment ID is required"
            )

        # -----------------------------------------------------
        # GET + LOCK
        # -----------------------------------------------------

        payment = (
            PaymentService
            .get_payment_by_razorpay_order(
                db=db,
                razorpay_order_id=razorpay_order_id,
            )
        )

        if not payment:
            raise ValueError(
                "Internal payment not found for webhook"
            )

        # -----------------------------------------------------
        # ALREADY CAPTURED
        # -----------------------------------------------------

        if payment.status == "CAPTURED":

            if (
                payment.razorpay_payment_id
                and payment.razorpay_payment_id
                != razorpay_payment_id
            ):
                raise ValueError(
                    "Webhook payment ID does not "
                    "match captured payment"
                )

            return payment

        # -----------------------------------------------------
        # VERIFY ORDER
        # -----------------------------------------------------

        if (
            payment.razorpay_order_id
            != razorpay_order_id
        ):
            raise ValueError(
                "Webhook Razorpay order ID does not "
                "match internal payment"
            )

        # -----------------------------------------------------
        # VERIFY AMOUNT
        # -----------------------------------------------------

        expected_amount = (
            PaymentService
            ._amount_in_smallest_unit(
                payment.amount
            )
        )

        try:
            webhook_amount = int(amount)
        except (
            ValueError,
            TypeError,
        ):
            webhook_amount = 0

        if webhook_amount != expected_amount:
            raise ValueError(
                "Webhook payment amount does not "
                "match internal payment"
            )

        # -----------------------------------------------------
        # VERIFY CURRENCY
        # -----------------------------------------------------

        expected_currency = str(
            payment.currency or "INR"
        ).upper()

        webhook_currency = str(
            currency or ""
        ).upper()

        if webhook_currency != expected_currency:
            raise ValueError(
                "Webhook payment currency does not "
                "match internal payment"
            )

        # -----------------------------------------------------
        # CAPTURE
        # -----------------------------------------------------

        payment = (
            PaymentService.capture_payment(
                db=db,
                payment=payment,
                razorpay_payment_id=(
                    razorpay_payment_id
                ),
                payment_method=payment_method,
            )
        )

        # -----------------------------------------------------
        # MARK ORDER PAID
        # -----------------------------------------------------

        try:

            PaymentService._mark_order_paid(
                db=db,
                payment=payment,
            )

        except Exception:

            db.rollback()
            raise

        db.commit()

        db.refresh(payment)

        return payment

    # =========================================================
    # WEBHOOK: PAYMENT FAILED
    # =========================================================

    @staticmethod
    def handle_webhook_payment_failed(
        db: Session,
        razorpay_order_id: str,
        razorpay_payment_id: Optional[str],
        failure_reason: str,
    ) -> Payment:

        if not razorpay_order_id:
            raise ValueError(
                "Webhook Razorpay order ID is required"
            )

        payment = (
            PaymentService
            .get_payment_by_razorpay_order(
                db=db,
                razorpay_order_id=razorpay_order_id,
            )
        )

        if not payment:
            raise ValueError(
                "Internal payment not found for webhook"
            )

        # -----------------------------------------------------
        # CAPTURED ALWAYS WINS
        #
        # A late failure webhook must NEVER downgrade a
        # captured payment.
        # -----------------------------------------------------

        if payment.status == "CAPTURED":
            return payment

        # -----------------------------------------------------
        # DUPLICATE FAILED WEBHOOK
        # -----------------------------------------------------

        if payment.status == "FAILED":
            return payment

        if razorpay_payment_id:

            if (
                payment.razorpay_payment_id
                and payment.razorpay_payment_id
                != razorpay_payment_id
            ):
                raise ValueError(
                    "Webhook payment ID does not "
                    "match internal payment"
                )

            payment.razorpay_payment_id = (
                razorpay_payment_id
            )

        reason = (
            failure_reason
            or "Razorpay payment failed"
        )

        PaymentService.fail_payment(
            db=db,
            payment=payment,
            failure_reason=reason,
        )

        try:

            OrderService.mark_payment_failed(
                db=db,
                order_id=payment.order_id,
                reason=reason,
                payment_id=payment.id,
            )

        except Exception:

            db.rollback()
            raise

        db.commit()

        db.refresh(payment)

        return payment

    # =========================================================
    # REFUND PAYMENT
    # =========================================================

    @staticmethod
    def refund_payment(
        db: Session,
        payment: Payment,
    ) -> Payment:

        if payment is None:
            raise ValueError(
                "Payment is required"
            )

        locked_payment = (
            db.query(Payment)
            .filter(
                Payment.id == payment.id
            )
            .with_for_update()
            .first()
        )

        if not locked_payment:
            raise ValueError(
                "Payment not found"
            )

        payment = locked_payment

        if payment.status == "REFUNDED":
            return payment

        if payment.status != "CAPTURED":
            raise ValueError(
                "Only captured payments can be refunded"
            )

        if not payment.razorpay_payment_id:
            raise ValueError(
                "Razorpay payment ID is missing"
            )

        old_status = payment.status

        try:

            if hasattr(
                RazorpayService,
                "refund_payment",
            ):

                refund_response = (
                    RazorpayService.refund_payment(
                        razorpay_payment_id=(
                            payment.razorpay_payment_id
                        ),
                        amount=(
                            PaymentService
                            ._amount_in_smallest_unit(
                                payment.amount
                            )
                        ),
                    )
                )

            elif hasattr(
                RazorpayService,
                "create_refund",
            ):

                refund_response = (
                    RazorpayService.create_refund(
                        razorpay_payment_id=(
                            payment.razorpay_payment_id
                        ),
                        amount=(
                            PaymentService
                            ._amount_in_smallest_unit(
                                payment.amount
                            )
                        ),
                    )
                )

            else:

                raise RuntimeError(
                    "RazorpayService does not provide "
                    "a refund method"
                )

        except Exception as e:

            AuditLogService.log_payment_event(
                db=db,
                merchant_id=payment.merchant_id,
                order_id=payment.order_id,
                payment_id=payment.id,
                event_type="PAYMENT_REFUND_FAILED",
                message=(
                    f"Refund failed for payment "
                    f"{payment.id}: {str(e)}"
                ),
                old_status=old_status,
                new_status=old_status,
                performed_by="PAYPILOT_PAYMENT_SYSTEM",
                commit=False,
            )

            db.flush()

            raise HTTPException(
                status_code=502,
                detail={
                    "message": (
                        "Unable to create Razorpay refund"
                    ),
                    "error": str(e),
                },
            )

        if refund_response is None:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Razorpay returned empty "
                    "refund response"
                ),
            )

        payment.status = "REFUNDED"
        payment.failure_reason = None

        db.flush()

        try:

            OrderService.mark_payment_refunded(
                db=db,
                order_id=payment.order_id,
                payment_id=payment.id,
            )

        except HTTPException:

            db.rollback()
            raise

        except Exception as e:

            db.rollback()

            raise HTTPException(
                status_code=409,
                detail={
                    "message": (
                        "Razorpay refund was created "
                        "but internal order refund "
                        "processing failed"
                    ),
                    "error": str(e),
                },
            )

        AuditLogService.log_payment_event(
            db=db,
            merchant_id=payment.merchant_id,
            order_id=payment.order_id,
            payment_id=payment.id,
            event_type="PAYMENT_REFUNDED",
            message=(
                f"Payment {payment.id} refunded successfully"
            ),
            old_status=old_status,
            new_status="REFUNDED",
            performed_by="PAYPILOT_PAYMENT_SYSTEM",
            commit=False,
        )

        return payment

    # =========================================================
    # CANCEL PAYMENT
    # =========================================================

    @staticmethod
    def cancel_payment(
        db: Session,
        payment: Payment,
    ) -> Payment:

        if payment is None:
            raise ValueError(
                "Payment is required"
            )

        if payment.status == "CAPTURED":
            raise ValueError(
                "Captured payment cannot be cancelled"
            )

        if payment.status == "REFUNDED":
            raise ValueError(
                "Refunded payment cannot be cancelled"
            )

        if payment.status == "CANCELLED":
            return payment

        old_status = payment.status

        payment.status = "CANCELLED"

        payment.failure_reason = (
            payment.failure_reason
            or "Payment cancelled"
        )

        db.flush()

        AuditLogService.log_payment_event(
            db=db,
            merchant_id=payment.merchant_id,
            order_id=payment.order_id,
            payment_id=payment.id,
            event_type="PAYMENT_CANCELLED",
            message=(
                f"Payment {payment.id} cancelled"
            ),
            old_status=old_status,
            new_status="CANCELLED",
            performed_by="PAYPILOT_PAYMENT_SYSTEM",
            commit=False,
        )

        return payment