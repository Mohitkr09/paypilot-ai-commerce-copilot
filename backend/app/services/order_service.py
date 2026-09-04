import json
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.product import Product
from app.models.payment import Payment
from app.models.manual_review import ManualReview
from app.models.audit_log import AuditLog

from app.services.risk_service import RiskService
from app.services.ai_service import AIService

from app.agents.graph.workflow import (
    build_paypilot_workflow,
)


class OrderService:

    # =========================================================
    # RISK ANALYSIS
    # =========================================================

    @staticmethod
    def analyze_order(
        quantity: int,
        discount_percent: float,
        final_amount: float,
    ):

        risk_data = RiskService.calculate_risk(
            quantity=quantity,
            discount_percent=discount_percent,
            final_amount=final_amount,
        )

        risk_score = risk_data.get(
            "risk_score",
            0,
        )

        try:
            risk_score = float(risk_score)
        except (TypeError, ValueError):
            risk_score = 0.0

        risk_score = max(
            0.0,
            min(
                risk_score,
                100.0,
            ),
        )

        risk_level = str(
            risk_data.get(
                "risk_level",
                "LOW",
            )
        ).upper()

        allowed_levels = {
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        }

        if risk_level not in allowed_levels:
            risk_level = "LOW"

        risk_reason = str(
            risk_data.get(
                "risk_reason",
                "",
            )
        )

        if risk_reason:
            risk_reasons = [
                reason.strip()
                for reason in risk_reason.split(";")
                if reason.strip()
            ]
        else:
            risk_reasons = []

        explanation = AIService.generate_explanation(
            quantity=quantity,
            requested_discount_percent=discount_percent,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_reasons=risk_reasons,
        )

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_reason": risk_reason,
            "risk_reasons": risk_reasons,
            "ai_explanation": explanation,
        }

    # =========================================================
    # REUSABLE RISK PROCESSOR
    # =========================================================

    @staticmethod
    def process_order_risk(
        quantity: int,
        discount_percent: float,
        final_amount: float,
    ):

        return OrderService.analyze_order(
            quantity=quantity,
            discount_percent=discount_percent,
            final_amount=final_amount,
        )

    # =========================================================
    # CREATE ORDER
    # =========================================================
    #
    # IMPORTANT:
    #
    # Inventory is NOT deducted here.
    #
    # Flow:
    #
    # Agent
    #   ↓
    # Risk / Policy
    #   ↓
    # Payment Gate
    #   ↓
    # APPROVED
    #       OR
    # MANUAL_REVIEW_REQUIRED
    #   ↓
    # Human approval if required
    #   ↓
    # Razorpay
    #   ↓
    # CAPTURED
    #   ↓
    # mark_payment_captured()
    #   ↓
    # Inventory deduction
    #   ↓
    # PAID
    #
    # =========================================================

    @staticmethod
    def create_order(
        db: Session,
        merchant_id: int,
        product_id: int,
        quantity: int,
        requested_discount_percent: float,
    ) -> Order:

        try:

            # =====================================================
            # 1. VALIDATION
            # =====================================================

            if quantity <= 0:

                raise HTTPException(
                    status_code=400,
                    detail="Quantity must be greater than zero",
                )

            if requested_discount_percent < 0:

                raise HTTPException(
                    status_code=400,
                    detail="Discount cannot be negative",
                )

            if requested_discount_percent > 100:

                raise HTTPException(
                    status_code=400,
                    detail="Discount cannot exceed 100%",
                )

            # =====================================================
            # 2. LOCK PRODUCT
            # =====================================================

            product = (
                db.query(Product)
                .filter(
                    Product.id == product_id
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
            # 3. MERCHANT VALIDATION
            # =====================================================

            if product.merchant_id != merchant_id:

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
            # 5. STOCK CHECK
            # =====================================================

            current_stock = (
                OrderService._get_product_stock(
                    product
                )
            )

            if current_stock < quantity:

                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Insufficient stock",
                        "available": current_stock,
                        "required": quantity,
                        "product_id": product_id,
                    },
                )

            # =====================================================
            # IMPORTANT
            #
            # DO NOT DEDUCT INVENTORY HERE.
            # =====================================================

            # =====================================================
            # 6. BUILD PAYPILOT WORKFLOW
            # =====================================================

            workflow = build_paypilot_workflow(db)

            # =====================================================
            # 7. INITIAL STATE
            # =====================================================

            initial_state = {

                "merchant_id": merchant_id,

                "product_id": product_id,

                "quantity": quantity,

                "requested_discount_percent": (
                    requested_discount_percent
                ),
            }

            # =====================================================
            # 8. RUN WORKFLOW
            # =====================================================

            try:

                result = workflow.invoke(
                    initial_state
                )

            except Exception as exc:

                db.rollback()

                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": (
                            "PayPilot workflow failed"
                        ),
                        "error": str(exc),
                    },
                )

            if not result:

                db.rollback()

                raise HTTPException(
                    status_code=500,
                    detail=(
                        "PayPilot workflow returned "
                        "no result"
                    ),
                )

            # =====================================================
            # 9. REQUIRED WORKFLOW OUTPUT
            # =====================================================

            required_fields = [
                "original_price",
                "final_price",
                "approved_discount_percent",
                "payment_gate_status",
            ]

            for field in required_fields:

                if field not in result:

                    db.rollback()

                    raise HTTPException(
                        status_code=500,
                        detail=(
                            "PayPilot workflow did not "
                            f"return {field}"
                        ),
                    )

            # =====================================================
            # 10. RISK
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

            risk_level = str(
                result.get(
                    "risk_level",
                    "LOW",
                )
            ).upper()

            allowed_risk_levels = {
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL",
            }

            if risk_level not in allowed_risk_levels:
                risk_level = "LOW"

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

            reasons_text = (
                "; ".join(risk_reasons)
                if risk_reasons
                else
                "No significant risk factors detected."
            )

            # =====================================================
            # 11. PRICING
            # =====================================================

            try:

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

            except (
                KeyError,
                TypeError,
                ValueError,
            ):

                db.rollback()

                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Invalid pricing information "
                        "returned by PayPilot"
                    ),
                )

            if original_price <= 0:

                raise HTTPException(
                    status_code=500,
                    detail="Invalid original product price",
                )

            if final_unit_price <= 0:

                raise HTTPException(
                    status_code=500,
                    detail="Invalid final product price",
                )

            if not 0 <= approved_discount <= 100:

                raise HTTPException(
                    status_code=500,
                    detail="Invalid approved discount",
                )

            maximum_safe_discount = round(
                float(
                    result.get(
                        "maximum_safe_discount_percent",
                        approved_discount,
                    )
                ),
                2,
            )

            final_margin = round(
                float(
                    result.get(
                        "final_margin_percent",
                        0,
                    )
                ),
                2,
            )

            discount_adjusted = bool(
                result.get(
                    "discount_adjusted",
                    False,
                )
            )

            # =====================================================
            # 12. ORDER AMOUNTS
            # =====================================================

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

            if final_amount <= 0:

                raise HTTPException(
                    status_code=500,
                    detail="Invalid final order amount",
                )

            if discount_amount < 0:
                discount_amount = 0.0

            # =====================================================
            # 13. PAYMENT GATE
            # =====================================================

            payment_gate_status = str(
                result.get(
                    "payment_gate_status",
                    "BLOCKED",
                )
            ).upper()

            payment_gate_reason = str(
                result.get(
                    "payment_gate_reason",
                    "",
                )
            ).strip()

            payment_approved = bool(
                result.get(
                    "payment_approved",
                    False,
                )
            )

            # =====================================================
            # PAYMENT GATE IS AUTHORITATIVE
            # =====================================================

            if payment_gate_status in {
                "APPROVED",
                "APPROVED_BY_MANUAL_REVIEW",
            }:

                payment_approved = True

            elif payment_gate_status in {
                "BLOCKED",
                "REJECTED_BY_MANUAL_REVIEW",
            }:

                payment_approved = False

            # =====================================================
            # 14. HARD BLOCK
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

                payment_gate_reason = " ".join(
                    hard_block_reasons
                )

            # =====================================================
            # 15. MANUAL REVIEW
            # =====================================================

            manual_review_required = bool(
                result.get(
                    "manual_review_required",
                    False,
                )
            )

            manual_review_decision = str(
                result.get(
                    "manual_review_decision",
                    "",
                )
            ).upper()

            # =====================================================
            # PENDING REVIEW ALWAYS BLOCKS PAYMENT
            # =====================================================

            if manual_review_required:

                payment_approved = False

                payment_gate_status = "BLOCKED"

                if not payment_gate_reason:

                    payment_gate_reason = (
                        "Order requires manual review "
                        "before payment can proceed."
                    )

            # =====================================================
            # MANUAL REJECT
            # =====================================================

            if manual_review_decision == "REJECT":

                payment_approved = False

                manual_review_required = False

                payment_gate_status = (
                    "REJECTED_BY_MANUAL_REVIEW"
                )

                payment_gate_reason = (
                    "Manual reviewer rejected the order."
                )

            # =====================================================
            # 16. FINAL ORDER STATUS
            # =====================================================

            if manual_review_required:

                order_status = (
                    "MANUAL_REVIEW_REQUIRED"
                )

            elif manual_review_decision == "REJECT":

                order_status = "REJECTED"

            elif payment_approved:

                order_status = "APPROVED"

            else:

                order_status = (
                    "MANUAL_REVIEW_REQUIRED"
                )

                manual_review_required = True

                payment_approved = False

                payment_gate_status = "BLOCKED"

                if not payment_gate_reason:

                    payment_gate_reason = (
                        "Order requires manual review "
                        "before payment can proceed."
                    )

            # =====================================================
            # 17. AI EXPLANATION
            # =====================================================

            explanation = result.get(
                "ai_explanation"
            )

            if not explanation:

                explanation = (
                    AIService.generate_explanation(
                        quantity=quantity,
                        requested_discount_percent=(
                            requested_discount_percent
                        ),
                        risk_score=risk_score,
                        risk_level=risk_level,
                        risk_reasons=risk_reasons,
                    )
                )

            if not explanation:
                explanation = {}

            if not isinstance(
                explanation,
                dict,
            ):

                explanation = {
                    "summary": str(
                        explanation
                    )
                }

            # =====================================================
            # 18. SERIALIZE RISK FACTORS
            # =====================================================

            risk_factors_json = (
                OrderService.serialize_risk_factors(
                    explanation
                )
            )

            ai_explanation = str(
                explanation.get(
                    "summary",
                    "",
                )
            ).strip()

            # =====================================================
            # 19. FACTOR EXPLANATION
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

            if not ai_explanation:

                ai_explanation = (
                    payment_gate_reason
                    or
                    str(
                        result.get(
                            "message",
                            "Order processed by PayPilot AI.",
                        )
                    )
                )

            # =====================================================
            # 20. CREATE ORDER
            # =====================================================

            order = Order(

                merchant_id=merchant_id,

                product_id=product_id,

                quantity=quantity,

                original_amount=original_amount,

                discount_percent=approved_discount,

                discount_amount=discount_amount,

                final_amount=final_amount,

                status=order_status,

                # -----------------------------
                # RISK
                # -----------------------------

                risk_score=risk_score,

                risk_level=risk_level,

                risk_reason=reasons_text,

                risk_factors=risk_factors_json,

                ai_explanation=ai_explanation,

                # -----------------------------
                # PAYMENT
                # -----------------------------

                payment_required=True,

                payment_approved=(
                    payment_approved
                ),

                payment_gate_status=(
                    payment_gate_status
                ),

                payment_gate_reason=(
                    payment_gate_reason
                ),

                # -----------------------------
                # MANUAL REVIEW
                # -----------------------------

                manual_review_required=(
                    manual_review_required
                ),

                # -----------------------------
                # DISCOUNT
                # -----------------------------

                requested_discount_percent=(
                    requested_discount_percent
                ),

                approved_discount_percent=(
                    approved_discount
                ),

                maximum_safe_discount_percent=(
                    maximum_safe_discount
                ),

                discount_adjusted=(
                    discount_adjusted
                ),

                # -----------------------------
                # FINANCIAL
                # -----------------------------

                final_price=final_unit_price,

                final_margin_percent=final_margin,

                # -----------------------------
                # EXPLANATION
                # -----------------------------

                decision_explanation=str(
                    result.get(
                        "decision_explanation",
                        "",
                    )
                ),

                final_explanation=str(
                    result.get(
                        "final_explanation",
                        ai_explanation,
                    )
                ),

                # -----------------------------
                # AGENT
                # -----------------------------

                processed_by=(
                    "PAYPILOT_AI_AGENT"
                ),

                # -----------------------------
                # INVENTORY
                # -----------------------------

                inventory_deducted=False,

                # -----------------------------
                # AUDIT
                # -----------------------------

                audit_event_type=(
                    result.get(
                        "audit_event_type",
                        "ORDER_DECISION",
                    )
                ),

                audit_performed_by=(
                    result.get(
                        "audit_performed_by",
                        "PAYPILOT_AI_AGENT",
                    )
                ),
            )

            db.add(order)

            # =====================================================
            # 21. FLUSH
            # =====================================================

            db.flush()

            if order.id is None:

                raise HTTPException(
                    status_code=500,
                    detail="Order ID was not generated",
                )

            # =====================================================
            # 22. AUDIT MESSAGE
            # =====================================================

            audit_message = str(
                result.get(
                    "audit_message",
                    "",
                )
            ).strip()

            if not audit_message:

                if order_status == "APPROVED":

                    audit_message = (
                        "Order approved by "
                        "PayPilot AI. "
                        "Payment is required before "
                        "inventory is committed."
                    )

                elif order_status == "REJECTED":

                    audit_message = (
                        "Order rejected by "
                        "PayPilot."
                    )

                else:

                    audit_message = (
                        "Order requires manual review "
                        "before payment can proceed."
                    )

            if payment_gate_reason:

                if (
                    payment_gate_reason.lower()
                    not in audit_message.lower()
                ):

                    audit_message += (
                        " Payment gate: "
                        + payment_gate_reason
                    )

            # =====================================================
            # 23. CREATE EXACTLY ONE AUDIT LOG
            # =====================================================

            audit_log = AuditLog(

                order_id=order.id,

                payment_id=None,

                merchant_id=merchant_id,

                event_type=(
                    result.get(
                        "audit_event_type",
                        "ORDER_DECISION",
                    )
                ),

                message=audit_message,

                old_status=(
                    result.get(
                        "audit_old_status",
                        "NEW",
                    )
                ),

                new_status=order_status,

                risk_score=risk_score,

                risk_level=risk_level,

                performed_by=(
                    result.get(
                        "audit_performed_by",
                        "PAYPILOT_AI_AGENT",
                    )
                ),
            )

            db.add(audit_log)

            # =====================================================
            # 24. CREATE MANUAL REVIEW
            # =====================================================

            if manual_review_required:

                manual_review_reason = (
                    payment_gate_reason
                    if payment_gate_reason
                    else (
                        reasons_text
                        if risk_reasons
                        else
                        "Payment was not "
                        "automatically approved."
                    )
                )

                manual_review = ManualReview(

                    order_id=order.id,

                    merchant_id=merchant_id,

                    reason=manual_review_reason,

                    risk_score=round(
                        risk_score,
                        2,
                    ),

                    risk_level=risk_level,

                    status="PENDING",
                )

                db.add(
                    manual_review
                )

            # =====================================================
            # IMPORTANT
            #
            # NEVER DEDUCT INVENTORY FOR MANUAL REVIEW.
            #
            # Human approval changes the order's payment
            # authorization state.
            #
            # Inventory is still deducted only after
            # Razorpay reports CAPTURED.
            # =====================================================

            # =====================================================
            # 25. COMMIT
            # =====================================================

            db.commit()

            # =====================================================
            # 26. REFRESH
            # =====================================================

            db.refresh(order)

            return order

        except HTTPException:

            db.rollback()

            raise

        except Exception as exc:

            db.rollback()

            raise HTTPException(
                status_code=500,
                detail={
                    "message": (
                        "Order creation failed"
                    ),
                    "error": str(exc),
                },
            )

    # =========================================================
    # MARK PAYMENT CAPTURED
    # =========================================================
    #
    # Razorpay CAPTURED
    #        ↓
    # this method
    #        ↓
    # inventory deduction
    #        ↓
    # PAID
    #
    # =========================================================

    @staticmethod
    def mark_payment_captured(
        db: Session,
        order_id: int,
        payment_id: Optional[int] = None,
    ) -> Order:

        try:

            # =====================================================
            # 1. LOCK ORDER
            # =====================================================

            order = (
                db.query(Order)
                .filter(
                    Order.id == order_id
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
            # 2. FIND PAYMENT
            # =====================================================

            if payment_id is None:

                payment = (
                    db.query(Payment)
                    .filter(
                        Payment.order_id
                        == order.id
                    )
                    .with_for_update()
                    .first()
                )

                if payment:

                    payment_id = payment.id

            # =====================================================
            # 3. IDEMPOTENCY
            # =====================================================

            if bool(
                getattr(
                    order,
                    "inventory_deducted",
                    False,
                )
            ):

                if order.status != "PAID":

                    order.status = "PAID"

                db.commit()

                db.refresh(order)

                return order

            # =====================================================
            # 4. VALID ORDER STATUS
            # =====================================================

            allowed_statuses = {
                "APPROVED",
                "PAYMENT_CAPTURED_STOCK_FAILED",
            }

            if order.status not in allowed_statuses:

                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": (
                            "Order is not in a valid "
                            "state for payment capture"
                        ),
                        "status": order.status,
                    },
                )

            # =====================================================
            # 5. MANUAL REVIEW GATE
            # =====================================================

            if bool(
                getattr(
                    order,
                    "manual_review_required",
                    False,
                )
            ):

                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Order is waiting for manual review. "
                        "Human approval is required "
                        "before payment can proceed."
                    ),
                )

            # =====================================================
            # 6. PAYMENT APPROVAL GATE
            # =====================================================

            if not bool(
                getattr(
                    order,
                    "payment_approved",
                    False,
                )
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Order payment was not approved "
                        "by the PayPilot payment gate"
                    ),
                )

            # =====================================================
            # 7. LOCK PRODUCT
            # =====================================================

            product = (
                db.query(Product)
                .filter(
                    Product.id
                    == order.product_id
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
            # 8. CURRENT STOCK
            # =====================================================

            current_stock = (
                OrderService._get_product_stock(
                    product
                )
            )

            old_status = order.status

            # =====================================================
            # 9. FINAL STOCK CHECK
            # =====================================================

            if current_stock < order.quantity:

                order.status = (
                    "PAYMENT_CAPTURED_STOCK_FAILED"
                )

                order.payment_gate_status = (
                    "PAYMENT_CAPTURED"
                )

                order.payment_gate_reason = (
                    "Payment captured successfully, "
                    "but inventory could not be committed."
                )

                order.final_explanation = (
                    "Payment was captured successfully, "
                    "but inventory could not be committed "
                    "because sufficient stock was unavailable. "
                    "Refund is required."
                )

                audit_log = AuditLog(

                    order_id=order.id,

                    payment_id=payment_id,

                    merchant_id=order.merchant_id,

                    event_type=(
                        "PAYMENT_CAPTURED_STOCK_FAILED"
                    ),

                    message=(
                        "Payment captured but inventory "
                        "could not be committed. "
                        f"Available: {current_stock}. "
                        f"Required: {order.quantity}. "
                        "Refund is required."
                    ),

                    old_status=old_status,

                    new_status=(
                        "PAYMENT_CAPTURED_STOCK_FAILED"
                    ),

                    risk_score=order.risk_score,

                    risk_level=order.risk_level,

                    performed_by=(
                        "PAYPILOT_PAYMENT_SYSTEM"
                    ),
                )

                db.add(audit_log)

                db.commit()

                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": (
                            "Payment captured but "
                            "inventory is insufficient"
                        ),
                        "available": current_stock,
                        "required": order.quantity,
                        "refund_required": True,
                        "order_id": order.id,
                        "payment_id": payment_id,
                    },
                )

            # =====================================================
            # 10. DEDUCT INVENTORY
            # =====================================================

            new_stock = (
                current_stock
                - int(order.quantity)
            )

            if new_stock < 0:

                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Inventory cannot become negative"
                    ),
                )

            OrderService._set_product_stock(
                product,
                new_stock,
            )

            # =====================================================
            # 11. INVENTORY FLAG
            # =====================================================

            order.inventory_deducted = True

            # =====================================================
            # 12. MARK ORDER PAID
            # =====================================================

            order.status = "PAID"

            order.payment_gate_status = "PAID"

            order.payment_gate_reason = (
                "Payment successfully captured by Razorpay."
            )

            order.final_explanation = (
                "Order approved by PayPilot, "
                "payment successfully captured, "
                "and inventory committed."
            )

            # =====================================================
            # 13. AUDIT
            # =====================================================

            audit_log = AuditLog(

                order_id=order.id,

                payment_id=payment_id,

                merchant_id=order.merchant_id,

                event_type="ORDER_PAID",

                message=(
                    "Payment captured successfully. "
                    "Inventory deducted and order "
                    "marked as PAID."
                ),

                old_status=old_status,

                new_status="PAID",

                risk_score=order.risk_score,

                risk_level=order.risk_level,

                performed_by=(
                    "PAYPILOT_PAYMENT_SYSTEM"
                ),
            )

            db.add(audit_log)

            # =====================================================
            # 14. COMMIT
            # =====================================================

            db.commit()

            db.refresh(order)

            return order

        except HTTPException:

            db.rollback()

            raise

        except Exception as exc:

            db.rollback()

            raise HTTPException(
                status_code=500,
                detail={
                    "message": (
                        "Payment capture processing failed"
                    ),
                    "error": str(exc),
                },
            )

    # =========================================================
    # PAYMENT FAILED
    # =========================================================

    @staticmethod
    def mark_payment_failed(
        db: Session,
        order_id: int,
        reason: str,
        payment_id: Optional[int] = None,
    ) -> Order:

        order = (
            db.query(Order)
            .filter(
                Order.id == order_id
            )
            .with_for_update()
            .first()
        )

        if not order:

            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        if bool(
            getattr(
                order,
                "inventory_deducted",
                False,
            )
        ):

            return order

        if order.status == "PAID":

            return order

        old_status = order.status

        payment_reason = (
            reason
            or
            "Payment failed"
        )

        order.status = "PAYMENT_FAILED"

        order.payment_gate_status = (
            "PAYMENT_FAILED"
        )

        order.payment_gate_reason = (
            payment_reason
        )

        order.final_explanation = (
            "Payment failed. "
            "Inventory was not deducted."
        )

        audit_log = AuditLog(

            order_id=order.id,

            payment_id=payment_id,

            merchant_id=order.merchant_id,

            event_type="PAYMENT_FAILED",

            message=(
                "Payment failed. "
                "Inventory was not deducted. "
                f"Reason: {payment_reason}"
            ),

            old_status=old_status,

            new_status="PAYMENT_FAILED",

            risk_score=order.risk_score,

            risk_level=order.risk_level,

            performed_by=(
                "PAYPILOT_PAYMENT_SYSTEM"
            ),
        )

        db.add(audit_log)

        db.commit()

        db.refresh(order)

        return order

    # =========================================================
    # REFUND ORDER
    # =========================================================

    @staticmethod
    def mark_order_refunded(
        db: Session,
        order_id: int,
        reason: str = "Payment refunded",
        payment_id: Optional[int] = None,
    ) -> Order:

        order = (
            db.query(Order)
            .filter(
                Order.id == order_id
            )
            .with_for_update()
            .first()
        )

        if not order:

            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        if order.status == "REFUNDED":

            return order

        inventory_was_deducted = bool(
            getattr(
                order,
                "inventory_deducted",
                False,
            )
        )

        # =====================================================
        # RESTORE INVENTORY ONLY IF IT WAS ACTUALLY DEDUCTED
        # =====================================================

        if inventory_was_deducted:

            product = (
                db.query(Product)
                .filter(
                    Product.id
                    == order.product_id
                )
                .with_for_update()
                .first()
            )

            if not product:

                raise HTTPException(
                    status_code=404,
                    detail=(
                        "Product not found while "
                        "restoring inventory"
                    ),
                )

            current_stock = (
                OrderService._get_product_stock(
                    product
                )
            )

            OrderService._set_product_stock(
                product,
                current_stock
                + int(order.quantity),
            )

            order.inventory_deducted = False

        old_status = order.status

        refund_reason = (
            reason
            or
            "Payment refunded"
        )

        order.status = "REFUNDED"

        order.payment_gate_status = (
            "REFUNDED"
        )

        order.payment_gate_reason = (
            refund_reason
        )

        if inventory_was_deducted:

            order.final_explanation = (
                "Payment refunded and inventory "
                "successfully restored."
            )

        else:

            order.final_explanation = (
                "Payment refunded. "
                "Inventory had not been deducted."
            )

        audit_log = AuditLog(

            order_id=order.id,

            payment_id=payment_id,

            merchant_id=order.merchant_id,

            event_type="PAYMENT_REFUNDED",

            message=(
                "Payment refunded successfully. "
                +
                (
                    "Inventory restored."
                    if inventory_was_deducted
                    else
                    "No inventory restoration was required."
                )
            ),

            old_status=old_status,

            new_status="REFUNDED",

            risk_score=order.risk_score,

            risk_level=order.risk_level,

            performed_by=(
                "PAYPILOT_PAYMENT_SYSTEM"
            ),
        )

        db.add(audit_log)

        db.commit()

        db.refresh(order)

        return order

    # =========================================================
    # PAYMENT SERVICE COMPATIBILITY
    # =========================================================

    @staticmethod
    def mark_payment_refunded(
        db: Session,
        order_id: int,
        reason: str = "Payment refunded",
        payment_id: Optional[int] = None,
    ) -> Order:

        return OrderService.mark_order_refunded(
            db=db,
            order_id=order_id,
            reason=reason,
            payment_id=payment_id,
        )

    # =========================================================
    # CANCEL ORDER
    # =========================================================

    @staticmethod
    def cancel_order(
        db: Session,
        order_id: int,
        reason: str = "Order cancelled",
    ) -> Order:

        order = (
            db.query(Order)
            .filter(
                Order.id == order_id
            )
            .with_for_update()
            .first()
        )

        if not order:

            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        if order.status == "CANCELLED":

            return order

        if order.status == "PAID":

            raise HTTPException(
                status_code=409,
                detail=(
                    "Paid order cannot be cancelled. "
                    "Use refund flow instead."
                ),
            )

        if order.status == (
            "PAYMENT_CAPTURED_STOCK_FAILED"
        ):

            raise HTTPException(
                status_code=409,
                detail=(
                    "Payment was captured. "
                    "Use refund flow instead."
                ),
            )

        old_status = order.status

        cancellation_reason = (
            reason
            or
            "Order cancelled"
        )

        order.status = "CANCELLED"

        order.payment_gate_status = (
            "CANCELLED"
        )

        order.payment_gate_reason = (
            cancellation_reason
        )

        order.final_explanation = (
            "Order cancelled before payment "
            "was captured. Inventory was not deducted."
        )

        audit_log = AuditLog(

            order_id=order.id,

            payment_id=None,

            merchant_id=order.merchant_id,

            event_type="ORDER_CANCELLED",

            message=cancellation_reason,

            old_status=old_status,

            new_status="CANCELLED",

            risk_score=order.risk_score,

            risk_level=order.risk_level,

            performed_by=(
                "PAYPILOT_ORDER_SYSTEM"
            ),
        )

        db.add(audit_log)

        db.commit()

        db.refresh(order)

        return order

    # =========================================================
    # GET ORDER
    # =========================================================

    @staticmethod
    def get_order(
        db: Session,
        order_id: int,
    ) -> Order:

        order = (
            db.query(Order)
            .filter(
                Order.id == order_id
            )
            .first()
        )

        if not order:

            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        return order

    # =========================================================
    # INVENTORY GETTER
    # =========================================================

    @staticmethod
    def _get_product_stock(
        product: Product,
    ) -> int:

        if hasattr(
            product,
            "stock_quantity",
        ):

            return int(
                product.stock_quantity or 0
            )

        if hasattr(
            product,
            "stock",
        ):

            return int(
                product.stock or 0
            )

        raise RuntimeError(
            "Product stock field not found"
        )

    # =========================================================
    # INVENTORY SETTER
    # =========================================================

    @staticmethod
    def _set_product_stock(
        product: Product,
        stock: int,
    ):

        if stock < 0:

            raise RuntimeError(
                "Product stock cannot be negative"
            )

        if hasattr(
            product,
            "stock_quantity",
        ):

            product.stock_quantity = stock

            return

        if hasattr(
            product,
            "stock",
        ):

            product.stock = stock

            return

        raise RuntimeError(
            "Product stock field not found"
        )

    # =========================================================
    # SERIALIZE RISK FACTORS
    # =========================================================

    @staticmethod
    def serialize_risk_factors(
        explanation: dict,
    ) -> str:

        return json.dumps(
            explanation,
            default=str,
        )

    # =========================================================
    # DESERIALIZE RISK FACTORS
    # =========================================================

    @staticmethod
    def deserialize_risk_factors(
        value,
    ):

        if not value:
            return None

        if isinstance(
            value,
            (dict, list),
        ):

            return value

        try:

            return json.loads(value)

        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):

            return None