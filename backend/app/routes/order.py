from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Header,
)
from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session

from app.db.database import get_db

from app.models.merchant import Merchant
from app.models.order import Order
from app.models.product import Product
from app.models.manual_review import ManualReview
from app.models.idempotency import IdempotencyKey

from app.schemas.order import (
    OrderCreate,
    OrderResponse,
)

from app.agents.graph.workflow import (
    build_paypilot_workflow,
)

from app.routes.events import broadcast_event

from app.services.ai_service import AIService
from app.services.order_service import OrderService
from app.services.audit_log_service import AuditLogService
from app.services.idempotency_service import (
    IdempotencyService,
)

# =========================================================
# AUTHENTICATION
# =========================================================

from app.auth.dependencies import (
    get_current_merchant,
)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


# =========================================================
# SERIALIZE ORDER
# =========================================================

def serialize_order(order: Order) -> dict:
    """
    Convert SQLAlchemy Order object into JSON-compatible data.
    """

    return (
        OrderResponse
        .model_validate(order)
        .model_dump(mode="json")
    )


# =========================================================
# SSE EVENT HELPER
# =========================================================

def build_order_event_data(
    order: Order,
    risk_reasons=None,
    risk_factors=None,
    message: str = "",
):
    """
    Build payload sent to frontend through SSE.

    IMPORTANT:
    Payment-gate state is included here so the frontend
    cannot display a successful payment gate when the
    database says otherwise.
    """

    return {
        "order_id": order.id,

        "merchant_id": order.merchant_id,

        "product_id": order.product_id,

        "quantity": order.quantity,

        "status": order.status,

        "original_amount": float(
            order.original_amount or 0
        ),

        "discount_percent": float(
            order.discount_percent or 0
        ),

        "discount_amount": float(
            order.discount_amount or 0
        ),

        "final_amount": float(
            order.final_amount or 0
        ),

        "risk_score": (
            float(order.risk_score)
            if order.risk_score is not None
            else None
        ),

        "risk_level": order.risk_level,

        "risk_reason": order.risk_reason,

        "risk_factors": (
            risk_factors
            if risk_factors is not None
            else []
        ),

        "risk_reasons": (
            risk_reasons
            if risk_reasons is not None
            else []
        ),

        "ai_explanation": order.ai_explanation,

        # =====================================================
        # PAYMENT GATE
        # =====================================================

        "payment_required": getattr(
            order,
            "payment_required",
            True,
        ),

        "payment_approved": getattr(
            order,
            "payment_approved",
            False,
        ),

        "payment_gate_status": getattr(
            order,
            "payment_gate_status",
            None,
        ),

        "payment_gate_reason": getattr(
            order,
            "payment_gate_reason",
            None,
        ),

        # =====================================================
        # MANUAL REVIEW
        # =====================================================

        "manual_review_required": getattr(
            order,
            "manual_review_required",
            False,
        ),

        "message": message,
    }


# =========================================================
# IDEMPOTENCY HELPER
# =========================================================

def handle_existing_idempotency(
    record: IdempotencyKey,
):
    """
    Handle a previously-used Idempotency-Key.
    """

    if IdempotencyService.is_completed(record):

        replay = IdempotencyService.replay(record)

        return JSONResponse(
            status_code=replay["status_code"],
            content=replay["body"],
        )

    if IdempotencyService.is_processing(record):

        raise HTTPException(
            status_code=409,
            detail=(
                "A request with this Idempotency-Key "
                "is already being processed"
            ),
        )

    if IdempotencyService.is_failed(record):

        raise HTTPException(
            status_code=409,
            detail=(
                "This Idempotency-Key was already used "
                "by a failed request"
            ),
        )

    raise HTTPException(
        status_code=500,
        detail="Invalid idempotency record status",
    )


# =========================================================
# INTERNAL ORDER CREATION
# =========================================================

async def create_order_internal(
    request: OrderCreate,
    db: Session,
    idempotency_record: Optional[IdempotencyKey] = None,
):
    """
    Main PayPilot order-processing pipeline.

    Authentication is performed by the public route
    before this function is called.

    This function intentionally does NOT use Depends()
    because it is also called internally by the AI Agent.

    Flow:

        Validate request
             ↓
        Lock product
             ↓
        Check stock
             ↓
        Run AI workflow
             ↓
        Calculate amount
             ↓
        Determine risk
             ↓
        Apply mandatory risk policy
             ↓
        Determine payment gate
             ↓
        Create order
             ↓
        Create ONE audit log
             ↓
        Manual review OR inventory deduction
             ↓
        Commit
             ↓
        SSE
             ↓
        Return
    """

    # =====================================================
    # 1. VALIDATE QUANTITY
    # =====================================================

    if request.quantity <= 0:

        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than zero",
        )

    # =====================================================
    # 2. GET + LOCK PRODUCT
    # =====================================================

    product = (
        db.query(Product)
        .filter(
            Product.id == request.product_id
        )
        .with_for_update()
        .first()
    )

    if not product:

        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    # =====================================================
    # 3. VERIFY MERCHANT
    # =====================================================

    if product.merchant_id != request.merchant_id:

        raise HTTPException(
            status_code=400,
            detail=(
                "Product does not belong "
                "to this merchant"
            ),
        )

    # =====================================================
    # 4. PRODUCT ACTIVE CHECK
    # =====================================================

    if hasattr(product, "is_active"):

        if not product.is_active:

            raise HTTPException(
                status_code=400,
                detail="Product is inactive",
            )

    elif hasattr(product, "active"):

        if not product.active:

            raise HTTPException(
                status_code=400,
                detail="Product is inactive",
            )

    # =====================================================
    # 5. STOCK
    # =====================================================

    if hasattr(product, "stock_quantity"):

        current_stock = int(
            product.stock_quantity or 0
        )

    elif hasattr(product, "stock"):

        current_stock = int(
            product.stock or 0
        )

    else:

        raise HTTPException(
            status_code=500,
            detail="Product stock field not found",
        )

    if current_stock < request.quantity:

        raise HTTPException(
            status_code=400,
            detail=(
                "Insufficient stock. "
                f"Available: {current_stock}"
            ),
        )

    # =====================================================
    # 6. BUILD WORKFLOW
    # =====================================================

    workflow = build_paypilot_workflow(db)

    # =====================================================
    # 7. INITIAL STATE
    # =====================================================

    initial_state = {
        "merchant_id": request.merchant_id,

        "product_id": request.product_id,

        "quantity": request.quantity,

        "requested_discount_percent": (
            request.requested_discount_percent
        ),
    }

    # =====================================================
    # 8. RUN WORKFLOW
    # =====================================================

    result = workflow.invoke(
        initial_state
    )

    if not result:

        raise RuntimeError(
            "AI workflow returned no result"
        )

    # =====================================================
    # 9. RISK SCORE
    # =====================================================

    try:

        risk_score = float(
            result.get(
                "risk_score",
                0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        risk_score = 0.0

    risk_score = max(
        0.0,
        min(
            risk_score,
            100.0,
        ),
    )

    # =====================================================
    # 10. RISK LEVEL
    # =====================================================

    risk_level = str(
        result.get(
            "risk_level",
            "LOW",
        )
    ).upper().strip()

    allowed_risk_levels = {
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    }

    if risk_level not in allowed_risk_levels:

        risk_level = "LOW"

    # =====================================================
    # 11. RISK REASONS
    # =====================================================

    risk_reasons = result.get(
        "risk_reasons",
        [],
    )

    if risk_reasons is None:

        risk_reasons = []

    if not isinstance(
        risk_reasons,
        list,
    ):

        risk_reasons = [
            str(risk_reasons)
        ]

    risk_reasons = [
        str(reason).strip()
        for reason in risk_reasons
        if str(reason).strip()
    ]

    risk_reasons = list(
        dict.fromkeys(
            risk_reasons
        )
    )

    # =====================================================
    # 12. REQUIRED WORKFLOW OUTPUT
    # =====================================================

    required_fields = [
        "original_price",
        "final_price",
        "approved_discount_percent",
    ]

    for field in required_fields:

        if field not in result:

            raise RuntimeError(
                f"AI workflow did not return {field}"
            )

    # =====================================================
    # 13. CALCULATE AMOUNTS
    # =====================================================

    quantity = int(
        request.quantity
    )

    original_price = float(
        result["original_price"]
    )

    final_unit_price = float(
        result["final_price"]
    )

    approved_discount = round(
        float(
            result[
                "approved_discount_percent"
            ]
        ),
        2,
    )

    original_amount = round(
        original_price * quantity,
        2,
    )

    final_amount = round(
        final_unit_price * quantity,
        2,
    )

    discount_amount = round(
        original_amount - final_amount,
        2,
    )

    if original_amount < 0:

        raise RuntimeError(
            "Invalid original order amount"
        )

    if final_amount < 0:

        raise RuntimeError(
            "Invalid final order amount"
        )

    if discount_amount < 0:

        discount_amount = 0.0

    # =====================================================
    # 14. PAYMENT GATE
    # =====================================================

    payment_gate_status = str(
        result.get(
            "payment_gate_status",
            "BLOCKED",
        )
    ).upper().strip()

    payment_gate_reason = str(
        result.get(
            "payment_gate_reason",
            "",
        )
    ).strip()

    payment_approved = (
        result.get(
            "payment_approved",
            False,
        )
        is True
    )

    approved_gate_statuses = {
        "APPROVED",
        "APPROVED_BY_MANUAL_REVIEW",
    }

    blocked_gate_statuses = {
        "BLOCKED",
        "REJECTED_BY_MANUAL_REVIEW",
    }

    if payment_gate_status in approved_gate_statuses:

        payment_approved = True

    elif payment_gate_status in blocked_gate_statuses:

        payment_approved = False

    # =====================================================
    # 15. HARD SAFETY GATES
    # =====================================================

    hard_block_reasons = result.get(
        "hard_block_reasons",
        [],
    )

    if hard_block_reasons is None:

        hard_block_reasons = []

    if not isinstance(
        hard_block_reasons,
        list,
    ):

        hard_block_reasons = [
            str(hard_block_reasons)
        ]

    hard_block_reasons = [
        str(reason).strip()
        for reason in hard_block_reasons
        if str(reason).strip()
    ]

    if hard_block_reasons:

        payment_approved = False

        payment_gate_status = "BLOCKED"

        payment_gate_reason = (
            " ".join(
                hard_block_reasons
            )
        )

    # =====================================================
    # 16. MANUAL REVIEW DECISION
    # =====================================================

    manual_review_decision = str(
        result.get(
            "manual_review_decision",
            "",
        )
    ).upper().strip()

    if (
        manual_review_decision == "REJECT"
        and payment_approved
    ):

        payment_approved = False

        payment_gate_status = (
            "REJECTED_BY_MANUAL_REVIEW"
        )

        payment_gate_reason = (
            "Manual reviewer rejected the order."
        )

    # =====================================================
    # 17. MANDATORY RISK POLICY
    # =====================================================

    if risk_level == "CRITICAL":

        payment_approved = False

        critical_reason = (
            "Critical risk detected. "
            "Order is blocked pending risk investigation."
        )

        if critical_reason not in risk_reasons:

            risk_reasons.append(
                critical_reason
            )

        payment_gate_status = "BLOCKED"

        payment_gate_reason = (
            critical_reason
        )

    elif risk_level == "HIGH":

        payment_approved = False

        high_reason = (
            "High risk detected. "
            "Order requires manual review."
        )

        if high_reason not in risk_reasons:

            risk_reasons.append(
                high_reason
            )

        payment_gate_status = "BLOCKED"

        payment_gate_reason = (
            high_reason
        )

    elif risk_level == "MEDIUM":

        payment_approved = False

        medium_reason = (
            "Medium risk detected. "
            "Order requires manual review."
        )

        if medium_reason not in risk_reasons:

            risk_reasons.append(
                medium_reason
            )

        payment_gate_status = "BLOCKED"

        payment_gate_reason = (
            medium_reason
        )

    # =====================================================
    # 18. NORMALIZE FINAL PAYMENT-GATE STATE
    # =====================================================
    #
    # IMPORTANT:
    #
    # These values are persisted to the database and later
    # used by PaymentService before Razorpay payment creation
    # and verification.
    #
    # Therefore we NEVER allow:
    #
    #     status = APPROVED
    #     payment_approved = false
    #     payment_gate_status = NULL
    #
    # =====================================================

    if payment_approved:

        payment_gate_status = "APPROVED"

        if not payment_gate_reason:

            payment_gate_reason = (
                "PayPilot payment gate approved "
                "the order for payment."
            )

    else:

        if (
            payment_gate_status
            not in {
                "BLOCKED",
                "REJECTED_BY_MANUAL_REVIEW",
            }
        ):

            payment_gate_status = "BLOCKED"

        if not payment_gate_reason:

            payment_gate_reason = (
                "PayPilot payment gate did not "
                "approve the order for automatic payment."
            )

    # =====================================================
    # 19. MANUAL REVIEW
    # =====================================================

    manual_review_required = (
        not payment_approved
    )

    # =====================================================
    # 20. ORDER STATUS
    # =====================================================

    if risk_level == "CRITICAL":

        order_status = "BLOCKED"

    elif manual_review_decision == "REJECT":

        order_status = "REJECTED"

        manual_review_required = False

    elif manual_review_required:

        order_status = (
            "MANUAL_REVIEW_REQUIRED"
        )

    else:

        order_status = "APPROVED"

    # =====================================================
    # 21. RISK REASON TEXT
    # =====================================================

    if risk_reasons:

        reasons_text = "; ".join(
            risk_reasons
        )

    else:

        reasons_text = (
            "No significant risk factors detected"
        )

    # =====================================================
    # 22. AI EXPLANATION
    # =====================================================

    explanation = AIService.generate_explanation(

        quantity=quantity,

        requested_discount_percent=(
            request.requested_discount_percent
        ),

        risk_score=risk_score,

        risk_level=risk_level,

        risk_reasons=risk_reasons,
    )

    if not explanation:

        explanation = {}

    # =====================================================
    # 23. SERIALIZE RISK FACTORS
    # =====================================================

    risk_factors_json = (
        OrderService.serialize_risk_factors(
            explanation
        )
    )

    # =====================================================
    # 24. AI SUMMARY
    # =====================================================

    ai_explanation = str(
        explanation.get(
            "summary",
            "",
        )
    ).strip()

    # =====================================================
    # 25. FACTORS
    # =====================================================

    factors = explanation.get(
        "factors",
        [],
    )

    if not isinstance(
        factors,
        list,
    ):

        factors = []

    factor_text = []

    for factor in factors:

        if not isinstance(
            factor,
            dict,
        ):

            continue

        factor_name = str(
            factor.get(
                "factor",
                "Unknown factor",
            )
        )

        factor_value = str(
            factor.get(
                "value",
                "",
            )
        )

        impact = str(
            factor.get(
                "impact",
                "",
            )
        )

        reason = str(
            factor.get(
                "reason",
                "",
            )
        )

        factor_text.append(
            (
                f"{factor_name}: "
                f"{factor_value} "
                f"({impact} impact). "
                f"{reason}"
            )
        )

    if factor_text:

        factors_string = " ".join(
            factor_text
        )

        if ai_explanation:

            ai_explanation += (
                " Risk factors: "
                + factors_string
            )

        else:

            ai_explanation = (
                "Risk factors: "
                + factors_string
            )

    # =====================================================
    # 26. FALLBACK EXPLANATION
    # =====================================================

    if not ai_explanation:

        if payment_gate_reason:

            ai_explanation = (
                payment_gate_reason
            )

        else:

            ai_explanation = str(
                result.get(
                    "message",
                    "Order processed by PayPilot AI.",
                )
            )

    # =====================================================
    # 27. CREATE ORDER
    # =====================================================

    order = Order(

        merchant_id=request.merchant_id,

        product_id=request.product_id,

        quantity=quantity,

        original_amount=original_amount,

        discount_percent=approved_discount,

        discount_amount=discount_amount,

        final_amount=final_amount,

        status=order_status,

        # =================================================
        # RISK
        # =================================================

        risk_score=risk_score,

        risk_level=risk_level,

        risk_reason=reasons_text,

        risk_factors=risk_factors_json,

        ai_explanation=ai_explanation,

        # =================================================
        # PAYMENT
        # =================================================
        #
        # THIS IS THE IMPORTANT FIX.
        #
        # These fields must be stored on the Order because
        # PaymentService reads them later.
        #
        # =================================================

        payment_required=True,

        payment_approved=payment_approved,

        payment_gate_status=(
            payment_gate_status
        ),

        payment_gate_reason=(
            payment_gate_reason
        ),

        # =================================================
        # MANUAL REVIEW
        # =================================================

        manual_review_required=(
            manual_review_required
        ),
    )

    db.add(order)

    # =====================================================
    # 28. FLUSH ORDER
    # =====================================================

    db.flush()

    if order.id is None:

        raise RuntimeError(
            "Order ID was not generated"
        )

    # =====================================================
    # 29. AUDIT MESSAGE
    # =====================================================

    audit_message = str(
        result.get(
            "audit_message",
            "",
        )
    ).strip()

    if risk_level == "CRITICAL":

        audit_message = (
            "CRITICAL risk order blocked. "
            "Manual investigation required."
        )

    elif risk_level == "HIGH":

        audit_message = (
            "HIGH risk order requires manual review."
        )

    elif risk_level == "MEDIUM":

        audit_message = (
            "MEDIUM risk order requires manual review."
        )

    elif not audit_message:

        if payment_approved:

            audit_message = (
                "Order approved successfully."
            )

        else:

            audit_message = (
                "Order requires manual review "
                "before payment can proceed."
            )

    # =====================================================
    # PAYMENT GATE REASON
    # =====================================================

    if (
        payment_gate_reason
        and payment_gate_reason.lower()
        not in audit_message.lower()
    ):

        audit_message += (
            " Payment gate: "
            + payment_gate_reason
        )

    # =====================================================
    # 30. EXACTLY ONE AUDIT LOG
    # =====================================================

    AuditLogService.create_log(

        db=db,

        merchant_id=request.merchant_id,

        order_id=order.id,

        event_type=str(
            result.get(
                "audit_event_type",
                "ORDER_DECISION",
            )
        ),

        message=audit_message,

        old_status=str(
            result.get(
                "audit_old_status",
                "NEW",
            )
        ),

        new_status=order_status,

        risk_score=risk_score,

        risk_level=risk_level,

        performed_by=str(
            result.get(
                "audit_performed_by",
                "PAYPILOT_AI_AGENT",
            )
        ),

        commit=False,
    )

    # =====================================================
    # 31. MANUAL REVIEW / INVENTORY
    # =====================================================

    if manual_review_required:

        manual_review_reason = (
            payment_gate_reason
            if payment_gate_reason
            else (
                reasons_text
                if risk_reasons
                else (
                    "Payment was not "
                    "automatically approved."
                )
            )
        )

        manual_review = ManualReview(

            order_id=order.id,

            merchant_id=request.merchant_id,

            reason=manual_review_reason,

            risk_score=round(
                risk_score,
                2,
            ),

            risk_level=risk_level,

            status="PENDING",
        )

        db.add(manual_review)

    else:

        if hasattr(
            product,
            "stock_quantity",
        ):

            product.stock_quantity -= quantity

            if product.stock_quantity < 0:

                raise RuntimeError(
                    "Product stock cannot be negative"
                )

        elif hasattr(
            product,
            "stock",
        ):

            product.stock -= quantity

            if product.stock < 0:

                raise RuntimeError(
                    "Product stock cannot be negative"
                )

        else:

            raise RuntimeError(
                "Product stock field not found"
            )

    # =====================================================
    # 32. FLUSH
    # =====================================================

    db.flush()

    # =====================================================
    # 33. SERIALIZE BEFORE IDEMPOTENCY
    # =====================================================

    response_data = serialize_order(
        order
    )

    # =====================================================
    # 34. COMPLETE IDEMPOTENCY
    # =====================================================

    if idempotency_record is not None:

        IdempotencyService.complete(

            db=db,

            record=idempotency_record,

            response_body=response_data,

            status_code=200,

            resource_type="ORDER",

            resource_id=order.id,
        )

    # =====================================================
    # 35. COMMIT ONCE
    # =====================================================

    db.commit()

    # =====================================================
    # 36. REFRESH
    # =====================================================

    db.refresh(order)

    # =====================================================
    # 37. SSE EVENT DATA
    # =====================================================

    event_data = build_order_event_data(

        order=order,

        risk_reasons=risk_reasons,

        risk_factors=factors,

        message=str(
            result.get(
                "message",
                (
                    "Order approved successfully."
                    if payment_approved
                    else
                    "Order requires manual review."
                ),
            )
        ),
    )

    # =====================================================
    # 38. ORDER CREATED EVENT
    # =====================================================

    try:

        await broadcast_event(
            "order_created",
            event_data,
        )

    except Exception as event_error:

        print(
            "SSE order_created error:",
            repr(event_error),
        )

    # =====================================================
    # 39. ORDER PROCESSED EVENT
    # =====================================================

    try:

        await broadcast_event(
            "order_processed",
            event_data,
        )

    except Exception as event_error:

        print(
            "SSE order_processed error:",
            repr(event_error),
        )

    # =====================================================
    # 40. RETURN
    # =====================================================

    return JSONResponse(
        status_code=200,
        content=serialize_order(order),
    )


# =========================================================
# POST /orders/
# =========================================================

@router.post(
    "/",
    response_model=OrderResponse,
)
async def create_order(

    request: OrderCreate,

    db: Session = Depends(get_db),

    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
    ),

    current_merchant: Merchant = Depends(
        get_current_merchant
    ),
):

    # =====================================================
    # AUTHORIZATION
    # =====================================================
    #
    # NEVER trust merchant_id sent by frontend.
    #
    # The JWT/session determines the real merchant.
    #
    # =====================================================

    if request.merchant_id != current_merchant.id:

        raise HTTPException(
            status_code=403,
            detail=(
                "You are not authorized to create "
                "orders for this merchant"
            ),
        )

    # =====================================================
    # 1. VALIDATE IDEMPOTENCY KEY
    # =====================================================

    try:

        idempotency_key = (
            IdempotencyService.validate_key(
                idempotency_key
            )
        )

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    # =====================================================
    # 2. START IDEMPOTENT OPERATION
    # =====================================================

    idempotency_record = None

    try:

        (
            idempotency_record,
            is_new,
        ) = IdempotencyService.start(

            db=db,

            merchant_id=current_merchant.id,

            operation="CREATE_ORDER",

            key=idempotency_key,

            request_payload=request,
        )

        # =================================================
        # 3. EXISTING REQUEST
        # =================================================

        if not is_new:

            return handle_existing_idempotency(
                idempotency_record
            )

        # =================================================
        # 4. CREATE ORDER
        # =================================================

        return await create_order_internal(

            request=request,

            db=db,

            idempotency_record=idempotency_record,
        )

    # =====================================================
    # HTTP EXCEPTION
    # =====================================================

    except HTTPException as e:

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

                    error_message=str(
                        e.detail
                    ),

                    status_code=e.status_code,
                )

                db.commit()

            except Exception as idempotency_error:

                db.rollback()

                print(
                    "IDEMPOTENCY FAILURE SAVE ERROR:",
                    repr(
                        idempotency_error
                    ),
                )

        raise

    # =====================================================
    # UNEXPECTED EXCEPTION
    # =====================================================

    except Exception as e:

        db.rollback()

        print(
            "CREATE ORDER ERROR:",
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
                    "IDEMPOTENCY FAILURE SAVE ERROR:",
                    repr(
                        idempotency_error
                    ),
                )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Order creation failed",
                "error": str(e),
            },
        )


# =========================================================
# GET ALL ORDERS
# =========================================================

@router.get(
    "/",
    response_model=list[OrderResponse],
)
def get_orders(

    db: Session = Depends(get_db),

    current_merchant: Merchant = Depends(
        get_current_merchant
    ),

):

    try:

        # =================================================
        # IMPORTANT:
        # Only return orders belonging to the
        # authenticated merchant.
        # =================================================

        orders = (
            db.query(Order)
            .filter(
                Order.merchant_id
                == current_merchant.id
            )
            .order_by(
                Order.id.desc()
            )
            .all()
        )

        return orders

    except Exception as e:

        print(
            "GET ORDERS ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to fetch orders",
                "error": str(e),
            },
        )


# =========================================================
# GET ORDER BY ID
# =========================================================

@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
def get_order(

    order_id: int,

    db: Session = Depends(get_db),

    current_merchant: Merchant = Depends(
        get_current_merchant
    ),

):

    try:

        # =================================================
        # IMPORTANT:
        # Filter by BOTH order ID and authenticated
        # merchant ID.
        #
        # This prevents:
        #
        # GET /orders/163
        #
        # from exposing another merchant's order.
        # =================================================

        order = (
            db.query(Order)
            .filter(
                Order.id == order_id,
                Order.merchant_id
                == current_merchant.id,
            )
            .first()
        )

        if not order:

            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        return order

    except HTTPException:

        raise

    except Exception as e:

        print(
            "GET ORDER ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to fetch order",
                "error": str(e),
            },
        )