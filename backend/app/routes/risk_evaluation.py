from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db

from app.models.order import Order
from app.models.risk_evaluation import RiskEvaluation

from app.services.risk_service import RiskService


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/risk-evaluations",
    tags=["Risk Evaluation"],
)


# =========================================================
# EVALUATE ORDER RISK
# =========================================================

@router.post("/{order_id}")
def evaluate_order_risk(
    order_id: int,
    db: Session = Depends(get_db),
):
    """
    Evaluate the risk of an order using RiskService.

    Risk is calculated using:

        - quantity
        - discount_percent
        - final_amount

    Existing risk evaluation for the order is updated.
    Otherwise a new evaluation is created.

    Possible results:

        LOW       -> APPROVE
        MEDIUM    -> REVIEW
        HIGH      -> REVIEW
        CRITICAL  -> BLOCK
    """

    # =====================================================
    # 1. FETCH ORDER
    # =====================================================

    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail=f"Order {order_id} not found",
        )

    # =====================================================
    # 2. GET ORDER VALUES
    # =====================================================

    quantity = order.quantity
    discount_percent = order.discount_percent
    final_amount = order.final_amount

    # =====================================================
    # 3. VALIDATE ORDER VALUES
    # =====================================================

    if quantity is None:
        raise HTTPException(
            status_code=400,
            detail="Order quantity is missing",
        )

    if final_amount is None:
        raise HTTPException(
            status_code=400,
            detail="Order final amount is missing",
        )

    # Discount is optional.
    # If missing, treat it as 0%.
    if discount_percent is None:
        discount_percent = 0.0

    # =====================================================
    # 4. SAFE CONVERSION
    # =====================================================

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Order quantity must be a valid integer",
        )

    try:
        discount_percent = float(discount_percent)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail=(
                "Order discount_percent must be "
                "a valid number"
            ),
        )

    try:
        final_amount = float(final_amount)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail=(
                "Order final_amount must be "
                "a valid number"
            ),
        )

    # =====================================================
    # 5. CALCULATE RISK
    # =====================================================

    try:

        risk_result = RiskService.calculate_risk(
            quantity=quantity,
            discount_percent=discount_percent,
            final_amount=final_amount,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unexpected error while calculating "
                f"order risk: {str(exc)}"
            ),
        )

    # =====================================================
    # 6. EXTRACT RISK RESULT
    # =====================================================

    risk_score = int(
        risk_result["risk_score"]
    )

    risk_level = str(
        risk_result["risk_level"]
    ).upper()

    risk_reason = str(
        risk_result["risk_reason"]
    )

    decision = str(
        risk_result["decision"]
    ).upper()

    # =====================================================
    # 7. CHECK EXISTING EVALUATION
    # =====================================================

    existing_evaluation = (
        db.query(RiskEvaluation)
        .filter(
            RiskEvaluation.order_id == order_id
        )
        .order_by(
            RiskEvaluation.id.desc()
        )
        .first()
    )

    # =====================================================
    # 8. UPDATE EXISTING EVALUATION
    # =====================================================

    if existing_evaluation:

        existing_evaluation.risk_score = (
            risk_score
        )

        existing_evaluation.risk_level = (
            risk_level
        )

        existing_evaluation.risk_reason = (
            risk_reason
        )

        try:

            db.commit()

            db.refresh(
                existing_evaluation
            )

        except Exception as exc:

            db.rollback()

            raise HTTPException(
                status_code=500,
                detail=(
                    "Failed to update risk evaluation: "
                    f"{str(exc)}"
                ),
            )

        return {
            "message": (
                "Risk evaluation updated successfully"
            ),

            "order_id": order_id,

            "risk_evaluation_id":
                existing_evaluation.id,

            "quantity": quantity,

            "discount_percent":
                discount_percent,

            "final_amount":
                final_amount,

            "risk_score":
                existing_evaluation.risk_score,

            "risk_level":
                existing_evaluation.risk_level,

            "risk_reason":
                existing_evaluation.risk_reason,

            "decision":
                decision,
        }

    # =====================================================
    # 9. CREATE NEW EVALUATION
    # =====================================================

    risk_evaluation = RiskEvaluation(
        order_id=order_id,
        risk_score=risk_score,
        risk_level=risk_level,
        risk_reason=risk_reason,
    )

    try:

        db.add(risk_evaluation)

        db.commit()

        db.refresh(
            risk_evaluation
        )

    except Exception as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to save risk evaluation: "
                f"{str(exc)}"
            ),
        )

    # =====================================================
    # 10. RETURN RESULT
    # =====================================================

    return {
        "message": (
            "Risk evaluation completed successfully"
        ),

        "order_id": order_id,

        "risk_evaluation_id":
            risk_evaluation.id,

        "quantity":
            quantity,

        "discount_percent":
            discount_percent,

        "final_amount":
            final_amount,

        "risk_score":
            risk_evaluation.risk_score,

        "risk_level":
            risk_evaluation.risk_level,

        "risk_reason":
            risk_evaluation.risk_reason,

        "decision":
            decision,
    }


# =========================================================
# GET RISK EVALUATION
# =========================================================

@router.get("/{order_id}")
def get_order_risk_evaluation(
    order_id: int,
    db: Session = Depends(get_db),
):
    """
    Get the latest stored risk evaluation
    for an order.
    """

    # =====================================================
    # 1. VERIFY ORDER EXISTS
    # =====================================================

    order = (
        db.query(Order)
        .filter(Order.id == order_id)
        .first()
    )

    if not order:

        raise HTTPException(
            status_code=404,
            detail=f"Order {order_id} not found",
        )

    # =====================================================
    # 2. FETCH LATEST RISK EVALUATION
    # =====================================================

    risk_evaluation = (
        db.query(RiskEvaluation)
        .filter(
            RiskEvaluation.order_id == order_id
        )
        .order_by(
            RiskEvaluation.id.desc()
        )
        .first()
    )

    if not risk_evaluation:

        raise HTTPException(
            status_code=404,
            detail=(
                f"No risk evaluation found "
                f"for order {order_id}"
            ),
        )

    # =====================================================
    # 3. CALCULATE BUSINESS DECISION
    # =====================================================

    try:

        decision = RiskService.get_decision(
            risk_level=risk_evaluation.risk_level
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    # =====================================================
    # 4. RETURN RESULT
    # =====================================================

    return {

        "id":
            risk_evaluation.id,

        "order_id":
            risk_evaluation.order_id,

        "risk_score":
            risk_evaluation.risk_score,

        "risk_level":
            risk_evaluation.risk_level,

        "risk_reason":
            risk_evaluation.risk_reason,

        "decision":
            decision,
    }