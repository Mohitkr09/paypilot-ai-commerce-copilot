import hashlib
import hmac
import json
import uuid

from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
)

from sqlalchemy.orm import Session

from app.db.database import get_db

from app.models.payment import Payment
from app.models.order import Order

from app.schemas.payment import (
    PaymentCreate,
    PaymentVerify,
    PaymentResponse,
)

from app.services.payment_service import PaymentService
from app.services.razorpay_service import RazorpayService
from app.services.order_service import OrderService
from app.services.idempotency_service import (
    IdempotencyService,
)

from app.core.config import settings


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)


# =========================================================
# HELPER
# =========================================================

def decimal_amount(value) -> Decimal:
    """
    Safely convert a monetary value to Decimal.
    """

    try:

        return Decimal(
            str(value)
        ).quantize(
            Decimal("0.01")
        )

    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ):

        raise ValueError(
            "Invalid monetary amount"
        )


# =========================================================
# IDEMPOTENCY HELPER
# =========================================================

def get_idempotency_key(
    idempotency_key: Optional[str],
) -> str:
    """Return a valid idempotency key.

    The frontend should send Idempotency-Key. For Razorpay's
    browser callback, generate a one-time key if the header is
    absent so a completed payment is not rejected only because
    the browser omitted the optional application header.
    """

    if idempotency_key is None or not str(idempotency_key).strip():
        return f"server-{uuid.uuid4().hex}"

    try:
        return IdempotencyService.validate_key(
            str(idempotency_key).strip()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


# =========================================================
# CREATE PAYMENT
# =========================================================

@router.post(
    "/",
    response_model=PaymentResponse,
)
def create_payment(
    request: PaymentCreate,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(
        default=None,
        alias="Idempotency-Key",
    ),
):
    """
    Create internal payment and Razorpay order.

    Idempotency:

        Same merchant
        + same operation
        + same Idempotency-Key
        + same request
            =
        replay previous result

    Same key + different request
        =
    HTTP 409

    Flow:

        Order
          ↓
        APPROVED
          ↓
        Payment Gate
          ↓
        Internal Payment
          ↓
        Razorpay Order
          ↓
        PENDING
    """

    idempotency_record = None

    try:

        # =====================================================
        # GET + LOCK ORDER FIRST
        # =====================================================
        # PaymentCreate intentionally contains only order_id and
        # currency. The merchant is derived from the trusted Order
        # record instead of being accepted from the client.

        order = (
            db.query(Order)
            .filter(
                Order.id == request.order_id
            )
            .with_for_update()
            .first()
        )

        if not order:

            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        merchant_id = order.merchant_id

        if merchant_id is None:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Order merchant_id is missing"
                ),
            )

        # =====================================================
        # VALIDATE IDEMPOTENCY KEY
        # =====================================================

        key = get_idempotency_key(
            idempotency_key
        )

        # =====================================================
        # IDEMPOTENCY REQUEST PAYLOAD
        # =====================================================

        idempotency_payload = {
            "merchant_id": merchant_id,
            "order_id": request.order_id,
            "currency": (
                request.currency
                or "INR"
            ),
        }

        # =====================================================
        # START IDEMPOTENT OPERATION
        # =====================================================

        try:

            (
                idempotency_record,
                is_new,
            ) = IdempotencyService.start(
                db=db,
                merchant_id=merchant_id,
                operation="CREATE_PAYMENT",
                key=key,
                request_payload=idempotency_payload,
            )

        except ValueError as e:

            raise HTTPException(
                status_code=409,
                detail=str(e),
            )

        # =====================================================
        # EXISTING REQUEST
        # =====================================================

        if not is_new:

            # -------------------------------------------------
            # COMPLETED
            # -------------------------------------------------

            if IdempotencyService.is_completed(
                idempotency_record
            ):

                replay = (
                    IdempotencyService.replay(
                        idempotency_record
                    )
                )

                db.commit()

                return replay["body"]

            # -------------------------------------------------
            # PROCESSING
            # -------------------------------------------------

            if IdempotencyService.is_processing(
                idempotency_record
            ):

                raise HTTPException(
                    status_code=409,
                    detail=(
                        "This payment request is "
                        "already being processed"
                    ),
                )

            # -------------------------------------------------
            # FAILED
            # -------------------------------------------------

            if IdempotencyService.is_failed(
                idempotency_record
            ):

                raise HTTPException(
                    status_code=409,
                    detail=(
                        "This Idempotency-Key was "
                        "already used for a failed "
                        "payment request"
                    ),
                )

        # =====================================================
        # ORDER STATUS
        # =====================================================

        if order.status != "APPROVED":

            raise HTTPException(
                status_code=400,
                detail=(
                    "Payment can only be created "
                    "for an approved order"
                ),
            )

        # =====================================================
        # PAYMENT GATE
        # =====================================================

        if not PaymentService._is_payment_approved(
            order
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Order was not approved by "
                    "the PayPilot payment gate"
                ),
            )

        # =====================================================
        # ORDER AMOUNT
        # =====================================================

        if order.final_amount is None:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Order final amount is missing"
                ),
            )

        try:

            amount = decimal_amount(
                order.final_amount
            )

        except ValueError:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid order final amount"
                ),
            )

        if amount <= 0:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Payment amount must be "
                    "greater than zero"
                ),
            )

        # =====================================================
        # CURRENCY
        # =====================================================

        currency = (
            request.currency
            or "INR"
        )

        try:

            currency = (
                PaymentService
                ._normalize_currency(
                    currency
                )
            )

        except ValueError as e:

            raise HTTPException(
                status_code=400,
                detail=str(e),
            )

        # =====================================================
        # FIND EXISTING PAYMENT
        # =====================================================

        payment = (
            db.query(Payment)
            .filter(
                Payment.order_id == order.id
            )
            .with_for_update()
            .first()
        )

        # =====================================================
        # EXISTING PAYMENT
        # =====================================================

        if payment:

            # -------------------------------------------------
            # CAPTURED
            # -------------------------------------------------

            if payment.status == "CAPTURED":

                response = PaymentResponse.model_validate(
                    payment
                )

                IdempotencyService.complete(
                    db=db,
                    record=idempotency_record,
                    response_body=response.model_dump(mode="json"),
                    status_code=200,
                    resource_type="PAYMENT",
                    resource_id=payment.id,
                )

                db.commit()
                db.refresh(payment)

                return payment

            # -------------------------------------------------
            # REFUNDED
            # -------------------------------------------------

            if payment.status == "REFUNDED":

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "This payment has already "
                        "been refunded"
                    ),
                )

            # -------------------------------------------------
            # CANCELLED
            # -------------------------------------------------

            if payment.status == "CANCELLED":

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "This payment has been cancelled"
                    ),
                )

            # -------------------------------------------------
            # VERIFY AMOUNT
            # -------------------------------------------------

            try:

                existing_amount = (
                    PaymentService._decimal_amount(
                        payment.amount
                    )
                )

            except ValueError:

                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Existing payment has "
                        "an invalid amount"
                    ),
                )

            if existing_amount != amount:

                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Existing payment amount "
                        "does not match order amount"
                    ),
                )

            # -------------------------------------------------
            # VERIFY CURRENCY
            # -------------------------------------------------

            existing_currency = (
                PaymentService._normalize_currency(
                    payment.currency
                )
            )

            if existing_currency != currency:

                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Existing payment currency "
                        "does not match requested currency"
                    ),
                )

            # -------------------------------------------------
            # ENSURE RAZORPAY ORDER
            # -------------------------------------------------

            if not payment.razorpay_order_id:

                payment = (
                    PaymentService
                    .create_razorpay_order(
                        db=db,
                        payment=payment,
                    )
                )

            # -------------------------------------------------
            # MARK PENDING
            # -------------------------------------------------

            elif payment.status == "CREATED":

                payment = (
                    PaymentService.mark_pending(
                        db=db,
                        payment=payment,
                    )
                )

            # -------------------------------------------------
            # SAVE IDEMPOTENCY RESPONSE
            # -------------------------------------------------

            response = PaymentResponse.model_validate(
                payment
            )

            IdempotencyService.complete(
                db=db,
                record=idempotency_record,
                response_body=response.model_dump(mode="json"),
                status_code=200,
                resource_type="PAYMENT",
                resource_id=payment.id,
            )

            # -------------------------------------------------
            # COMMIT
            # -------------------------------------------------

            db.commit()
            db.refresh(payment)

            return payment

        # =====================================================
        # CREATE INTERNAL PAYMENT
        # =====================================================

        try:

            payment = (
                PaymentService.create_payment(
                    db=db,
                    order=order,
                    currency=currency,
                )
            )

        except ValueError as e:

            raise HTTPException(
                status_code=400,
                detail=str(e),
            )

        # =====================================================
        # CREATE RAZORPAY ORDER
        # =====================================================

        payment = (
            PaymentService.create_razorpay_order(
                db=db,
                payment=payment,
            )
        )

        # =====================================================
        # RESPONSE
        # =====================================================

        response = PaymentResponse.model_validate(
            payment
        )

        # =====================================================
        # COMPLETE IDEMPOTENCY
        # =====================================================

        IdempotencyService.complete(
            db=db,
            record=idempotency_record,
            response_body=response.model_dump(mode="json"),
            status_code=200,
            resource_type="PAYMENT",
            resource_id=payment.id,
        )

        # =====================================================
        # COMMIT
        # =====================================================

        db.commit()
        db.refresh(payment)

        return payment

    except HTTPException as e:

        db.rollback()

        # Persist failure for a newly-created idempotency record.
        # This prevents a failed key from remaining PROCESSING.
        if (
            idempotency_record is not None
            and IdempotencyService.is_processing(
                idempotency_record
            )
        ):
            try:
                IdempotencyService.fail(
                    db=db,
                    record=idempotency_record,
                    error_message=str(e.detail),
                    status_code=e.status_code,
                )
                db.commit()
            except Exception as idempotency_error:
                db.rollback()
                print(
                    "PAYMENT IDEMPOTENCY FAILURE SAVE ERROR:",
                    repr(idempotency_error),
                )

        raise

    except Exception as e:

        db.rollback()

        print(
            "CREATE PAYMENT ERROR:",
            repr(e),
        )

        if (
            idempotency_record is not None
            and IdempotencyService.is_processing(
                idempotency_record
            )
        ):
            try:
                IdempotencyService.fail(
                    db=db,
                    record=idempotency_record,
                    error_message=str(e),
                    status_code=500,
                )
                db.commit()
            except Exception as idempotency_error:
                db.rollback()
                print(
                    "PAYMENT IDEMPOTENCY FAILURE SAVE ERROR:",
                    repr(idempotency_error),
                )

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Payment creation failed"
                ),
                "error": str(e),
            },
        )


# =========================================================
# INITIALIZE PAYMENT
# =========================================================

@router.post(
    "/{payment_id}/initialize",
    response_model=PaymentResponse,
)
def initialize_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(
        default=None,
        alias="Idempotency-Key",
    ),
):
    """
    Ensure an existing payment has a Razorpay order.

    This endpoint is also idempotent.
    """

    idempotency_record = None

    try:

        # =====================================================
        # GET PAYMENT
        # =====================================================

        payment = (
            db.query(Payment)
            .filter(
                Payment.id == payment_id
            )
            .with_for_update()
            .first()
        )

        if not payment:

            raise HTTPException(
                status_code=404,
                detail="Payment not found",
            )

        # =====================================================
        # IDEMPOTENCY
        # =====================================================

        key = get_idempotency_key(
            idempotency_key
        )

        payload = {
            "payment_id": payment_id,
        }

        try:

            (
                idempotency_record,
                is_new,
            ) = IdempotencyService.start(
                db=db,
                merchant_id=payment.merchant_id,
                operation="INITIALIZE_PAYMENT",
                key=key,
                request_payload=payload,
            )

        except ValueError as e:

            raise HTTPException(
                status_code=409,
                detail=str(e),
            )

        if not is_new:

            if IdempotencyService.is_completed(
                idempotency_record
            ):

                replay = (
                    IdempotencyService.replay(
                        idempotency_record
                    )
                )

                db.commit()

                return replay["body"]

            if IdempotencyService.is_processing(
                idempotency_record
            ):

                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Payment initialization "
                        "is already being processed"
                    ),
                )

            if IdempotencyService.is_failed(
                idempotency_record
            ):

                raise HTTPException(
                    status_code=409,
                    detail=(
                        "This Idempotency-Key was "
                        "already used for a failed "
                        "initialization"
                    ),
                )

        # =====================================================
        # CAPTURED
        # =====================================================

        if payment.status == "CAPTURED":

            response = PaymentResponse.model_validate(
                payment
            )

            IdempotencyService.complete(
                db=db,
                record=idempotency_record,
                response_body=response,
                status_code=200,
                resource_type="PAYMENT",
                resource_id=payment.id,
            )

            db.commit()

            return payment

        # =====================================================
        # TERMINAL STATES
        # =====================================================

        if payment.status == "REFUNDED":

            raise HTTPException(
                status_code=400,
                detail=(
                    "Refunded payment cannot "
                    "be initialized"
                ),
            )

        if payment.status == "CANCELLED":

            raise HTTPException(
                status_code=400,
                detail=(
                    "Cancelled payment cannot "
                    "be initialized"
                ),
            )

        # =====================================================
        # GET ORDER
        # =====================================================

        order = (
            db.query(Order)
            .filter(
                Order.id == payment.order_id
            )
            .with_for_update()
            .first()
        )

        if not order:

            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        # =====================================================
        # ORDER STATUS
        # =====================================================

        if order.status != "APPROVED":

            raise HTTPException(
                status_code=400,
                detail=(
                    "Payment can only be initialized "
                    "for an approved order"
                ),
            )

        # =====================================================
        # PAYMENT GATE
        # =====================================================

        if not PaymentService._is_payment_approved(
            order
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Order was not approved by "
                    "the PayPilot payment gate"
                ),
            )

        # =====================================================
        # CREATE RAZORPAY ORDER
        # =====================================================

        if not payment.razorpay_order_id:

            payment = (
                PaymentService
                .create_razorpay_order(
                    db=db,
                    payment=payment,
                )
            )

        elif payment.status == "CREATED":

            payment = (
                PaymentService.mark_pending(
                    db=db,
                    payment=payment,
                )
            )

        # =====================================================
        # SAVE IDEMPOTENCY RESPONSE
        # =====================================================

        response = PaymentResponse.model_validate(
            payment
        )

        IdempotencyService.complete(
            db=db,
            record=idempotency_record,
            response_body=response,
            status_code=200,
            resource_type="PAYMENT",
            resource_id=payment.id,
        )

        # =====================================================
        # COMMIT
        # =====================================================

        db.commit()
        db.refresh(payment)

        return payment

    except HTTPException:

        db.rollback()
        raise

    except Exception as e:

        db.rollback()

        print(
            "INITIALIZE PAYMENT ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Payment initialization failed"
                ),
                "error": str(e),
            },
        )


# =========================================================
# VERIFY PAYMENT
# =========================================================

@router.post(
    "/{payment_id}/verify",
    response_model=PaymentResponse,
)
def verify_payment(
    payment_id: int,
    request: PaymentVerify,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(
        default=None,
        alias="Idempotency-Key",
    ),
):
    """
    Verify a Razorpay Checkout payment and finalize the order.

    IMPORTANT:

    The frontend is never trusted for payment success. The backend:

        1. Loads the internal payment.
        2. Confirms the Razorpay order ID belongs to that payment.
        3. Verifies the Razorpay HMAC signature.
        4. Fetches the real payment from Razorpay.
        5. Confirms payment ID, order ID, amount and currency.
        6. If Razorpay says AUTHORIZED, attempts capture.
        7. Requires the final Razorpay state to be CAPTURED.
        8. Marks the internal payment CAPTURED.
        9. Marks the order PAID and deducts inventory exactly once.

    This endpoint is idempotent. A repeated successful verification is
    safe and returns the already-captured payment.
    """

    idempotency_record = None

    try:
        # =====================================================
        # 1. GET + LOCK INTERNAL PAYMENT
        # =====================================================

        payment = (
            db.query(Payment)
            .filter(Payment.id == payment_id)
            .with_for_update()
            .first()
        )

        if not payment:
            raise HTTPException(
                status_code=404,
                detail="Payment not found",
            )

        # =====================================================
        # 2. VALIDATE RAZORPAY CALLBACK DATA
        # =====================================================

        razorpay_order_id = str(
            request.razorpay_order_id or ""
        ).strip()
        razorpay_payment_id = str(
            request.razorpay_payment_id or ""
        ).strip()
        razorpay_signature = str(
            request.razorpay_signature or ""
        ).strip()

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

        # =====================================================
        # 3. IDEMPOTENCY
        # =====================================================

        key = get_idempotency_key(idempotency_key)

        payload = {
            "payment_id": payment_id,
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
            "payment_method": request.payment_method,
        }

        try:
            (
                idempotency_record,
                is_new,
            ) = IdempotencyService.start(
                db=db,
                merchant_id=payment.merchant_id,
                operation="VERIFY_PAYMENT",
                key=key,
                request_payload=payload,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=409,
                detail=str(e),
            )

        if not is_new:
            if IdempotencyService.is_completed(
                idempotency_record
            ):
                replay = IdempotencyService.replay(
                    idempotency_record
                )
                db.commit()
                return replay["body"]

            if IdempotencyService.is_processing(
                idempotency_record
            ):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Payment verification is already "
                        "being processed"
                    ),
                )

            if IdempotencyService.is_failed(
                idempotency_record
            ):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "This Idempotency-Key was already "
                        "used for a failed verification"
                    ),
                )

        # =====================================================
        # 4. INTERNAL RAZORPAY ORDER ID CHECK
        # =====================================================

        if not payment.razorpay_order_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Payment has not been initialized "
                    "with a Razorpay order"
                ),
            )

        if payment.razorpay_order_id != razorpay_order_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Razorpay order ID does not match "
                    "the internal payment"
                ),
            )

        # =====================================================
        # 5. ALREADY CAPTURED
        # =====================================================

        if payment.status == "CAPTURED":
            # Keep the callback identifiers up to date if they are
            # missing, but never perform the capture twice.
            if not payment.razorpay_payment_id:
                payment.razorpay_payment_id = (
                    razorpay_payment_id
                )
            if not payment.razorpay_signature:
                payment.razorpay_signature = (
                    razorpay_signature
                )
            if request.payment_method and not payment.payment_method:
                payment.payment_method = request.payment_method

            response = PaymentResponse.model_validate(payment)
            response_body = response.model_dump(mode="json")

            if idempotency_record is not None:
                IdempotencyService.complete(
                    db=db,
                    record=idempotency_record,
                    response_body=response_body,
                    status_code=200,
                    resource_type="PAYMENT",
                    resource_id=payment.id,
                )

            db.commit()
            db.refresh(payment)
            return payment

        # =====================================================
        # 6. TERMINAL INTERNAL STATES
        # =====================================================

        if payment.status == "REFUNDED":
            raise HTTPException(
                status_code=400,
                detail="Refunded payment cannot be verified",
            )

        if payment.status == "CANCELLED":
            raise HTTPException(
                status_code=400,
                detail="Cancelled payment cannot be verified",
            )

        # =====================================================
        # 7. VERIFY RAZORPAY SIGNATURE
        # =====================================================
        # Do this BEFORE trusting any payment information returned by
        # the browser. Razorpay's signature is HMAC-SHA256 of:
        #
        #     razorpay_order_id + "|" + razorpay_payment_id
        #
        # The secret remains only on the backend.

        try:
            try:
                signature_valid = (
                    RazorpayService.verify_payment(
                        razorpay_order_id=razorpay_order_id,
                        razorpay_payment_id=razorpay_payment_id,
                        razorpay_signature=razorpay_signature,
                    )
                )
            except AttributeError:
                signature_valid = (
                    RazorpayService.verify_payment_signature(
                        razorpay_order_id=razorpay_order_id,
                        razorpay_payment_id=razorpay_payment_id,
                        razorpay_signature=razorpay_signature,
                    )
                )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Razorpay signature verification failed: "
                    f"{e}"
                ),
            )

        if not signature_valid:
            try:
                PaymentService.fail_payment(
                    db=db,
                    payment=payment,
                    failure_reason=(
                        "Invalid Razorpay payment signature"
                    ),
                )
                db.commit()
            except Exception:
                db.rollback()

            raise HTTPException(
                status_code=400,
                detail="Invalid Razorpay payment signature",
            )

        # =====================================================
        # 8. FETCH REAL PAYMENT FROM RAZORPAY
        # =====================================================

        try:
            razorpay_payment = RazorpayService.get_payment(
                razorpay_payment_id
            )
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Unable to fetch payment from Razorpay: "
                    f"{e}"
                ),
            )

        if not razorpay_payment:
            raise HTTPException(
                status_code=400,
                detail="Razorpay returned an empty payment response",
            )

        # =====================================================
        # 9. VERIFY PAYMENT ID
        # =====================================================

        returned_payment_id = str(
            razorpay_payment.get("id") or ""
        ).strip()

        if returned_payment_id != razorpay_payment_id:
            raise HTTPException(
                status_code=400,
                detail="Invalid Razorpay payment ID",
            )

        # =====================================================
        # 10. VERIFY RAZORPAY ORDER ID
        # =====================================================

        returned_order_id = str(
            razorpay_payment.get("order_id") or ""
        ).strip()

        if returned_order_id != razorpay_order_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Razorpay payment does not belong "
                    "to this Razorpay order"
                ),
            )

        # =====================================================
        # 11. VERIFY AMOUNT
        # =====================================================

        expected_amount = int(
            decimal_amount(payment.amount) * Decimal("100")
        )

        try:
            returned_amount = int(
                razorpay_payment.get("amount")
            )
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400,
                detail="Invalid amount returned by Razorpay",
            )

        if returned_amount != expected_amount:
            try:
                PaymentService.fail_payment(
                    db=db,
                    payment=payment,
                    failure_reason=(
                        "Razorpay payment amount does not "
                        "match internal payment amount"
                    ),
                )
                db.commit()
            except Exception:
                db.rollback()

            raise HTTPException(
                status_code=400,
                detail=(
                    "Razorpay payment amount does not match "
                    "internal payment amount"
                ),
            )

        # =====================================================
        # 12. VERIFY CURRENCY
        # =====================================================

        returned_currency = str(
            razorpay_payment.get("currency") or ""
        ).upper().strip()
        expected_currency = str(
            payment.currency or "INR"
        ).upper().strip()

        if returned_currency != expected_currency:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Razorpay payment currency does not "
                    "match internal payment currency"
                ),
            )

        # =====================================================
        # 13. CHECK RAZORPAY STATUS
        # =====================================================

        razorpay_status = str(
            razorpay_payment.get("status") or ""
        ).upper().strip()

        print()
        print("=" * 60)
        print("RAZORPAY PAYMENT VERIFICATION")
        print("=" * 60)
        print("Internal Payment ID:", payment.id)
        print("Internal Order ID:", payment.order_id)
        print("Razorpay Order ID:", razorpay_order_id)
        print("Razorpay Payment ID:", razorpay_payment_id)
        print("Amount:", returned_amount)
        print("Currency:", returned_currency)
        print("Razorpay Status:", razorpay_status)
        print("=" * 60)

        # =====================================================
        # 14. AUTHORIZED -> TRY CAPTURE
        # =====================================================

        if razorpay_status == "AUTHORIZED":
            try:
                capture_result = RazorpayService.capture_payment(
                    razorpay_payment_id=razorpay_payment_id,
                    amount=payment.amount,
                    currency=expected_currency,
                )
            except Exception as e:
                # The payment may have changed to captured between
                # the initial fetch and this capture attempt. Fetch it
                # again before deciding that verification failed.
                try:
                    razorpay_payment = RazorpayService.get_payment(
                        razorpay_payment_id
                    )
                    razorpay_status = str(
                        razorpay_payment.get("status") or ""
                    ).upper().strip()
                except Exception:
                    razorpay_status = "AUTHORIZED"

                if razorpay_status != "CAPTURED":
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Razorpay payment is authorized but "
                            "could not be captured: "
                            f"{e}"
                        ),
                    )
            else:
                # Capture succeeded; use the capture response when it
                # contains the final payment representation.
                if isinstance(capture_result, dict):
                    razorpay_payment = capture_result

                razorpay_status = str(
                    razorpay_payment.get("status") or ""
                ).upper().strip()

                # Some Razorpay responses may not include status in the
                # capture response. Fetch the authoritative state.
                if razorpay_status != "CAPTURED":
                    try:
                        razorpay_payment = RazorpayService.get_payment(
                            razorpay_payment_id
                        )
                        razorpay_status = str(
                            razorpay_payment.get("status") or ""
                        ).upper().strip()
                    except Exception as e:
                        raise HTTPException(
                            status_code=502,
                            detail=(
                                "Payment capture succeeded but the "
                                "final Razorpay payment status could "
                                f"not be confirmed: {e}"
                            ),
                        )

        # =====================================================
        # 15. CAPTURED -> FINALIZE INTERNAL PAYMENT + ORDER
        # =====================================================

        if razorpay_status == "CAPTURED":
            payment_method = (
                request.payment_method
                or razorpay_payment.get("method")
            )

            payment = PaymentService.capture_payment(
                db=db,
                payment=payment,
                razorpay_payment_id=razorpay_payment_id,
                razorpay_signature=razorpay_signature,
                payment_method=payment_method,
            )

            # -------------------------------------------------
            # IMPORTANT:
            #
            # Payment CAPTURED alone is not the final order state.
            # This call marks the order PAID and deducts inventory
            # exactly once using OrderService's locking/idempotency.
            # -------------------------------------------------

            OrderService.mark_payment_captured(
                db=db,
                order_id=payment.order_id,
            )

            db.flush()

            response = PaymentResponse.model_validate(payment)
            response_body = response.model_dump(mode="json")

            IdempotencyService.complete(
                db=db,
                record=idempotency_record,
                response_body=response_body,
                status_code=200,
                resource_type="PAYMENT",
                resource_id=payment.id,
            )

            db.commit()
            db.refresh(payment)

            print()
            print("=" * 60)
            print("CHECKOUT PAYMENT VERIFIED SUCCESSFULLY")
            print("=" * 60)
            print("Payment ID:", payment.id)
            print("Razorpay Payment ID:", payment.razorpay_payment_id)
            print("Payment Status:", payment.status)
            print("Order ID:", payment.order_id)
            print("Order Status: PAID")
            print("=" * 60)

            return payment

        # =====================================================
        # 16. FAILED
        # =====================================================

        if razorpay_status == "FAILED":
            reason = (
                razorpay_payment.get("error_description")
                or razorpay_payment.get("error_reason")
                or razorpay_payment.get("error_code")
                or "Razorpay payment failed"
            )

            try:
                PaymentService.fail_payment(
                    db=db,
                    payment=payment,
                    failure_reason=str(reason),
                )

                try:
                    OrderService.mark_payment_failed(
                        db=db,
                        order_id=payment.order_id,
                        reason=str(reason),
                    )
                except Exception:
                    # Payment failure is still recorded even if the
                    # optional order-state update is unavailable.
                    db.rollback()
                    PaymentService.fail_payment(
                        db=db,
                        payment=payment,
                        failure_reason=str(reason),
                    )

                db.commit()
            except HTTPException:
                db.rollback()
                raise
            except Exception:
                db.rollback()

            raise HTTPException(
                status_code=400,
                detail=(
                    "Payment was not successful. Razorpay status: "
                    f"FAILED. Reason: {reason}"
                ),
            )

        # =====================================================
        # 17. OTHER / NOT CAPTURED
        # =====================================================

        raise HTTPException(
            status_code=409,
            detail=(
                "Payment is not captured yet. "
                "Current Razorpay status: "
                f"{razorpay_status or 'UNKNOWN'}"
            ),
        )

    except HTTPException as e:
        db.rollback()

        # Do not leave an idempotency record stuck in PROCESSING.
        if (
            idempotency_record is not None
            and IdempotencyService.is_processing(
                idempotency_record
            )
        ):
            try:
                IdempotencyService.fail(
                    db=db,
                    record=idempotency_record,
                    error_message=str(e.detail),
                    status_code=e.status_code,
                )
                db.commit()
            except Exception:
                db.rollback()

        print()
        print("=" * 60)
        print("VERIFY PAYMENT HTTP ERROR")
        print("=" * 60)
        print("Payment ID:", payment_id)
        print("Status:", e.status_code)
        print("Detail:", e.detail)
        print("=" * 60)

        raise

    except Exception as e:
        db.rollback()

        if (
            idempotency_record is not None
            and IdempotencyService.is_processing(
                idempotency_record
            )
        ):
            try:
                IdempotencyService.fail(
                    db=db,
                    record=idempotency_record,
                    error_message=str(e),
                    status_code=500,
                )
                db.commit()
            except Exception:
                db.rollback()

        print()
        print("=" * 60)
        print("VERIFY PAYMENT UNEXPECTED ERROR")
        print("=" * 60)
        print("Payment ID:", payment_id)
        print("ERROR:", repr(e))
        print("=" * 60)

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Payment verification failed",
                "error": str(e),
            },
        )


# =========================================================
# RAZORPAY WEBHOOK
# =========================================================

@router.post(
    "/webhook",
)
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_razorpay_signature: str | None = Header(
        default=None,
        alias="X-Razorpay-Signature",
    ),
):
    """
    Razorpay webhook.

    Supported:

        payment.captured
        payment.failed
        refund.created

    Webhooks use Razorpay's own signature and therefore
    do not use application Idempotency-Key headers.
    """

    print()
    print("=" * 60)
    print("RAZORPAY WEBHOOK RECEIVED")
    print("=" * 60)

    # =====================================================
    # WEBHOOK SECRET
    # =====================================================

    webhook_secret = str(
        getattr(
            settings,
            "RAZORPAY_WEBHOOK_SECRET",
            "",
        )
        or ""
    ).strip()

    if not webhook_secret:

        raise HTTPException(
            status_code=500,
            detail=(
                "Razorpay webhook secret "
                "is not configured"
            ),
        )

    # =====================================================
    # SIGNATURE
    # =====================================================

    if not x_razorpay_signature:

        raise HTTPException(
            status_code=400,
            detail=(
                "Missing Razorpay webhook signature"
            ),
        )

    signature = (
        x_razorpay_signature.strip()
    )

    # =====================================================
    # RAW BODY
    # =====================================================

    body = await request.body()

    if not body:

        raise HTTPException(
            status_code=400,
            detail="Empty webhook body",
        )

    # =====================================================
    # HMAC
    # =====================================================

    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(
        expected_signature,
        signature,
    ):

        print(
            "INVALID RAZORPAY WEBHOOK SIGNATURE"
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid Razorpay webhook signature"
            ),
        )

    # =====================================================
    # PARSE JSON
    # =====================================================

    try:

        payload = json.loads(
            body.decode("utf-8")
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid webhook JSON",
        )

    event = payload.get("event")

    print(
        "Webhook event:",
        event,
    )

    # =====================================================
    # PAYMENT CAPTURED
    # =====================================================

    if event == "payment.captured":

        try:

            payment_entity = (
                payload
                .get("payload", {})
                .get("payment", {})
                .get("entity", {})
            )

            razorpay_payment_id = (
                payment_entity.get("id")
            )

            razorpay_order_id = (
                payment_entity.get("order_id")
            )

            amount = payment_entity.get(
                "amount"
            )

            currency = payment_entity.get(
                "currency"
            )

            method = payment_entity.get(
                "method"
            )

            if not razorpay_payment_id:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Webhook payment ID is missing"
                    ),
                )

            if not razorpay_order_id:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Webhook order ID is missing"
                    ),
                )

            payment = (
                db.query(Payment)
                .filter(
                    Payment.razorpay_order_id
                    == razorpay_order_id
                )
                .with_for_update()
                .first()
            )

            if not payment:

                return {
                    "success": True,
                    "processed": False,
                    "event": event,
                    "message": (
                        "No matching internal payment"
                    ),
                }

            # -------------------------------------------------
            # IDEMPOTENT WEBHOOK
            # -------------------------------------------------

            if payment.status == "CAPTURED":

                return {
                    "success": True,
                    "processed": False,
                    "event": event,
                    "payment_id": payment.id,
                    "order_id": payment.order_id,
                    "status": payment.status,
                    "message": (
                        "Payment already captured"
                    ),
                }

            # -------------------------------------------------
            # PAYMENT IDENTITY
            # -------------------------------------------------

            if (
                payment.razorpay_payment_id
                and
                payment.razorpay_payment_id
                != razorpay_payment_id
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Razorpay payment ID does not "
                        "match internal payment"
                    ),
                )

            # -------------------------------------------------
            # AMOUNT
            # -------------------------------------------------

            if amount is not None:

                try:

                    webhook_amount = int(
                        amount
                    )

                    internal_amount = (
                        PaymentService
                        ._amount_in_smallest_unit(
                            payment.amount
                        )
                    )

                except (
                    ValueError,
                    TypeError,
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Invalid webhook amount"
                        ),
                    )

                if (
                    webhook_amount
                    != internal_amount
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Webhook amount does not "
                            "match internal payment"
                        ),
                    )

            # -------------------------------------------------
            # CURRENCY
            # -------------------------------------------------

            if currency:

                if (
                    str(currency).upper()
                    != str(
                        payment.currency
                    ).upper()
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Webhook currency does not "
                            "match internal payment"
                        ),
                    )

            # -------------------------------------------------
            # CAPTURE
            # -------------------------------------------------

            PaymentService.capture_payment(
                db=db,
                payment=payment,
                razorpay_payment_id=(
                    razorpay_payment_id
                ),
                payment_method=method,
            )

            # -------------------------------------------------
            # MARK ORDER PAID
            # -------------------------------------------------

            OrderService.mark_payment_captured(
                db=db,
                order_id=payment.order_id,
                payment_id=payment.id,
            )

            # -------------------------------------------------
            # COMMIT
            # -------------------------------------------------

            db.commit()
            db.refresh(payment)

            print(
                "RAZORPAY PAYMENT CAPTURED:",
                payment.id,
            )

            return {
                "success": True,
                "processed": True,
                "event": event,
                "payment_id": payment.id,
                "order_id": payment.order_id,
                "status": payment.status,
            }

        except HTTPException:

            db.rollback()
            raise

        except Exception as e:

            db.rollback()

            print(
                "PAYMENT CAPTURE WEBHOOK ERROR:",
                repr(e),
            )

            raise HTTPException(
                status_code=500,
                detail={
                    "message": (
                        "Payment webhook processing failed"
                    ),
                    "error": str(e),
                },
            )

    # =====================================================
    # PAYMENT FAILED
    # =====================================================

    if event == "payment.failed":

        try:

            payment_entity = (
                payload
                .get("payload", {})
                .get("payment", {})
                .get("entity", {})
            )

            razorpay_payment_id = (
                payment_entity.get("id")
            )

            razorpay_order_id = (
                payment_entity.get("order_id")
            )

            reason = (
                payment_entity.get(
                    "error_description"
                )
                or payment_entity.get(
                    "error_reason"
                )
                or "Razorpay payment failed"
            )

            if not razorpay_order_id:

                return {
                    "success": True,
                    "processed": False,
                    "event": event,
                    "message": (
                        "No Razorpay order ID"
                    ),
                }

            payment = (
                db.query(Payment)
                .filter(
                    Payment.razorpay_order_id
                    == razorpay_order_id
                )
                .with_for_update()
                .first()
            )

            if not payment:

                return {
                    "success": True,
                    "processed": False,
                    "event": event,
                    "message": (
                        "No matching internal payment"
                    ),
                }

            # -------------------------------------------------
            # NEVER FAIL CAPTURED PAYMENT
            # -------------------------------------------------

            if payment.status == "CAPTURED":

                return {
                    "success": True,
                    "processed": False,
                    "event": event,
                    "payment_id": payment.id,
                    "message": (
                        "Payment already captured"
                    ),
                }

            # -------------------------------------------------
            # IDEMPOTENCY
            # -------------------------------------------------

            if payment.status == "FAILED":

                return {
                    "success": True,
                    "processed": False,
                    "event": event,
                    "payment_id": payment.id,
                    "status": payment.status,
                    "message": (
                        "Payment already marked failed"
                    ),
                }

            if razorpay_payment_id:

                payment.razorpay_payment_id = (
                    razorpay_payment_id
                )

            PaymentService.fail_payment(
                db=db,
                payment=payment,
                failure_reason=str(reason),
            )

            try:

                OrderService.mark_payment_failed(
                    db=db,
                    order_id=payment.order_id,
                    reason=str(reason),
                    payment_id=payment.id,
                )

            except TypeError:

                OrderService.mark_payment_failed(
                    db=db,
                    order_id=payment.order_id,
                    reason=str(reason),
                )

            db.commit()
            db.refresh(payment)

            return {
                "success": True,
                "processed": True,
                "event": event,
                "payment_id": payment.id,
                "status": payment.status,
            }

        except HTTPException:

            db.rollback()
            raise

        except Exception as e:

            db.rollback()

            print(
                "PAYMENT FAILED WEBHOOK ERROR:",
                repr(e),
            )

            raise HTTPException(
                status_code=500,
                detail={
                    "message": (
                        "Payment failure webhook "
                        "processing failed"
                    ),
                    "error": str(e),
                },
            )

    # =====================================================
    # REFUND CREATED
    # =====================================================

    if event == "refund.created":

        try:

            refund_entity = (
                payload
                .get("payload", {})
                .get("refund", {})
                .get("entity", {})
            )

            razorpay_payment_id = (
                refund_entity.get(
                    "payment_id"
                )
            )

            if not razorpay_payment_id:

                return {
                    "success": True,
                    "processed": False,
                    "event": event,
                    "message": (
                        "No payment ID in refund event"
                    ),
                }

            payment = (
                db.query(Payment)
                .filter(
                    Payment.razorpay_payment_id
                    == razorpay_payment_id
                )
                .with_for_update()
                .first()
            )

            if not payment:

                return {
                    "success": True,
                    "processed": False,
                    "event": event,
                    "message": (
                        "No matching internal payment"
                    ),
                }

            if payment.status == "REFUNDED":

                return {
                    "success": True,
                    "processed": False,
                    "event": event,
                    "payment_id": payment.id,
                    "status": payment.status,
                    "message": (
                        "Payment already refunded"
                    ),
                }

            if payment.status != "CAPTURED":

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Only captured payments "
                        "can be refunded"
                    ),
                )

            old_status = payment.status

            payment.status = "REFUNDED"
            payment.failure_reason = None

            db.flush()

            OrderService.mark_payment_refunded(
                db=db,
                order_id=payment.order_id,
                payment_id=payment.id,
            )

            from app.services.audit_log_service import (
                AuditLogService,
            )

            AuditLogService.log_payment_event(
                db=db,
                merchant_id=payment.merchant_id,
                order_id=payment.order_id,
                payment_id=payment.id,
                event_type="PAYMENT_REFUNDED",
                message=(
                    f"Payment {payment.id} "
                    f"refunded successfully"
                ),
                old_status=old_status,
                new_status="REFUNDED",
                performed_by="RAZORPAY",
                commit=False,
            )

            db.commit()
            db.refresh(payment)

            return {
                "success": True,
                "processed": True,
                "event": event,
                "payment_id": payment.id,
                "status": payment.status,
            }

        except HTTPException:

            db.rollback()
            raise

        except Exception as e:

            db.rollback()

            print(
                "REFUND WEBHOOK ERROR:",
                repr(e),
            )

            raise HTTPException(
                status_code=500,
                detail={
                    "message": (
                        "Refund webhook processing failed"
                    ),
                    "error": str(e),
                },
            )

    # =====================================================
    # OTHER EVENTS
    # =====================================================

    print(
        "Webhook event not handled:",
        event,
    )

    return {
        "success": True,
        "processed": False,
        "event": event,
        "message": "Webhook received",
    }


# =========================================================
# GET ALL PAYMENTS
# =========================================================

@router.get(
    "/",
    response_model=list[PaymentResponse],
)
def get_payments(
    db: Session = Depends(get_db),
):

    return (
        db.query(Payment)
        .order_by(
            Payment.id.desc()
        )
        .all()
    )


# =========================================================
# GET PAYMENT BY ID
# =========================================================

@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
):

    payment = (
        db.query(Payment)
        .filter(
            Payment.id == payment_id
        )
        .first()
    )

    if not payment:

        raise HTTPException(
            status_code=404,
            detail="Payment not found",
        )

    return payment


# =========================================================
# GET PAYMENT BY ORDER
# =========================================================

@router.get(
    "/order/{order_id}",
    response_model=PaymentResponse,
)
def get_payment_by_order(
    order_id: int,
    db: Session = Depends(get_db),
):

    payment = (
        db.query(Payment)
        .filter(
            Payment.order_id == order_id
        )
        .first()
    )

    if not payment:

        raise HTTPException(
            status_code=404,
            detail=(
                "Payment not found for this order"
            ),
        )

    return payment


# =========================================================
# PAYMENT STATUS
# =========================================================

@router.get(
    "/{payment_id}/status",
)
def get_payment_status(
    payment_id: int,
    db: Session = Depends(get_db),
):

    payment = (
        db.query(Payment)
        .filter(
            Payment.id == payment_id
        )
        .first()
    )

    if not payment:

        raise HTTPException(
            status_code=404,
            detail="Payment not found",
        )

    return {
        "payment_id": payment.id,
        "order_id": payment.order_id,
        "merchant_id": payment.merchant_id,
        "status": payment.status,
        "amount": (
            float(payment.amount)
            if payment.amount is not None
            else None
        ),
        "currency": payment.currency,
        "razorpay_order_id": (
            payment.razorpay_order_id
        ),
        "razorpay_payment_id": (
            payment.razorpay_payment_id
        ),
        "payment_method": (
            payment.payment_method
        ),
        "failure_reason": (
            payment.failure_reason
        ),
    }


# =========================================================
# REFUND PAYMENT
# =========================================================

@router.post(
    "/{payment_id}/refund",
)
def refund_payment(
    payment_id: int,
    db: Session = Depends(get_db),
):

    try:

        payment = (
            db.query(Payment)
            .filter(
                Payment.id == payment_id
            )
            .with_for_update()
            .first()
        )

        if not payment:

            raise HTTPException(
                status_code=404,
                detail="Payment not found",
            )

        # =====================================================
        # IDEMPOTENCY
        # =====================================================

        if payment.status == "REFUNDED":

            db.commit()

            return {
                "message": (
                    "Payment has already been refunded"
                ),
                "success": True,
                "payment": payment,
            }

        # =====================================================
        # CAPTURED ONLY
        # =====================================================

        if payment.status != "CAPTURED":

            raise HTTPException(
                status_code=400,
                detail=(
                    "Only captured payments "
                    "can be refunded"
                ),
            )

        # =====================================================
        # RAZORPAY PAYMENT ID
        # =====================================================

        if not payment.razorpay_payment_id:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Razorpay payment ID is missing"
                ),
            )

        # =====================================================
        # REFUND
        # =====================================================

        payment = (
            PaymentService.refund_payment(
                db=db,
                payment=payment,
            )
        )

        # =====================================================
        # COMMIT
        # =====================================================

        db.commit()
        db.refresh(payment)

        return {
            "message": (
                "Payment refunded successfully"
            ),
            "success": True,
            "payment": payment,
        }

    except HTTPException:

        db.rollback()
        raise

    except Exception as e:

        db.rollback()

        print(
            "REFUND PAYMENT ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Payment refund failed"
                ),
                "error": str(e),
            },
        )