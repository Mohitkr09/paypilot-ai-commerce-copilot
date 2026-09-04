from sqlalchemy.orm import Session

from app.models.merchant import Merchant
from app.models.product import Product

from app.agents.graph.state import PayPilotState


# =========================================================
# POLICY AGENT
# =========================================================
#
# Loads merchant/product policy and inventory.
#
# IMPORTANT:
# Large quantity is NOT itself a hard block.
# The order is allowed to continue as long as sufficient
# stock exists.
#
# =========================================================

def policy_agent(
    state: PayPilotState,
    db: Session,
) -> PayPilotState:

    merchant_id = state.get("merchant_id")
    product_id = state.get("product_id")

    if merchant_id is None:
        raise ValueError("Merchant ID is required")

    if product_id is None:
        raise ValueError("Product ID is required")

    # =====================================================
    # MERCHANT
    # =====================================================

    merchant = (
        db.query(Merchant)
        .filter(Merchant.id == merchant_id)
        .first()
    )

    if not merchant:
        raise ValueError("Merchant not found")

    # =====================================================
    # PRODUCT
    # =====================================================

    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if not product:
        raise ValueError("Product not found")

    # =====================================================
    # MERCHANT VALIDATION
    # =====================================================

    if not merchant.is_active:
        raise ValueError("Merchant is inactive")

    # =====================================================
    # PRODUCT-MERCHANT VALIDATION
    # =====================================================

    if product.merchant_id != merchant.id:
        raise ValueError(
            "Product does not belong to merchant"
        )

    # =====================================================
    # PRODUCT VALIDATION
    # =====================================================

    if not product.is_active:
        raise ValueError("Product is inactive")

    price = float(product.price or 0)
    cost_price = float(product.cost_price or 0)
    stock_quantity = int(product.stock_quantity or 0)

    if price <= 0:
        raise ValueError(
            "Product price must be greater than zero"
        )

    if cost_price < 0:
        raise ValueError(
            "Product cost price cannot be negative"
        )

    if stock_quantity < 0:
        raise ValueError(
            "Product stock cannot be negative"
        )

    # =====================================================
    # MERCHANT POLICY
    # =====================================================

    maximum_discount = float(
        merchant.maximum_discount_percent or 0
    )

    minimum_margin = float(
        merchant.minimum_margin or 0
    )

    auto_payment_limit = float(
        merchant.auto_payment_limit or 0
    )

    if not 0 <= maximum_discount <= 100:
        raise ValueError(
            "Merchant maximum discount must be between 0 and 100%"
        )

    if not 0 <= minimum_margin < 100:
        raise ValueError(
            "Merchant minimum margin must be between 0 and 99.99%"
        )

    if auto_payment_limit <= 0:
        raise ValueError(
            "Automatic payment limit must be greater than zero"
        )

    # =====================================================
    # MERCHANT STATE
    # =====================================================

    state["merchant_name"] = merchant.name
    state["merchant_active"] = bool(
        merchant.is_active
    )

    state["maximum_discount_percent"] = (
        maximum_discount
    )

    state["minimum_margin"] = minimum_margin

    state["auto_payment_limit"] = (
        auto_payment_limit
    )

    state["bundle_allowed"] = bool(
        getattr(
            merchant,
            "bundle_allowed",
            False,
        )
    )

    # =====================================================
    # PRODUCT STATE
    # =====================================================

    state["product_name"] = product.name

    state["original_price"] = price

    state["cost_price"] = cost_price

    state["stock_quantity"] = stock_quantity

    state["product_active"] = bool(
        product.is_active
    )

    # =====================================================
    # POLICY STATUS
    # =====================================================

    state["policy_loaded"] = True

    state["policy_explanation"] = (
        "Merchant policy loaded successfully. "
        f"Maximum discount: "
        f"{maximum_discount:.2f}%. "
        f"Minimum margin: "
        f"{minimum_margin:.2f}%. "
        f"Automatic payment limit: "
        f"{auto_payment_limit:.2f}. "
        f"Available stock: "
        f"{stock_quantity}."
    )

    return state


# =========================================================
# DECISION AGENT
# =========================================================
#
# Calculates financially safe pricing.
#
# =========================================================

def decision_agent(
    state: PayPilotState,
) -> PayPilotState:

    price = float(
        state["original_price"]
    )

    cost_price = float(
        state["cost_price"]
    )

    minimum_margin = float(
        state["minimum_margin"]
    )

    requested_discount = float(
        state.get(
            "requested_discount_percent",
            0,
        )
    )

    merchant_max_discount = float(
        state["maximum_discount_percent"]
    )

    quantity = int(
        state["quantity"]
    )

    # =====================================================
    # VALIDATION
    # =====================================================

    if quantity <= 0:
        raise ValueError(
            "Quantity must be greater than zero"
        )

    if requested_discount < 0:
        raise ValueError(
            "Discount cannot be negative"
        )

    if requested_discount > 100:
        raise ValueError(
            "Discount cannot exceed 100%"
        )

    if price <= 0:
        raise ValueError(
            "Product price must be greater than zero"
        )

    if cost_price < 0:
        raise ValueError(
            "Product cost price cannot be negative"
        )

    if not 0 <= minimum_margin < 100:
        raise ValueError(
            "Minimum margin must be between 0 and 99.99%"
        )

    # =====================================================
    # MINIMUM SAFE PRICE
    # =====================================================

    denominator = (
        1 - minimum_margin / 100
    )

    if denominator <= 0:
        raise ValueError(
            "Invalid minimum margin configuration"
        )

    minimum_safe_price = (
        cost_price / denominator
    )

    # =====================================================
    # MAXIMUM SAFE DISCOUNT
    # =====================================================

    maximum_safe_discount = (
        (
            price
            - minimum_safe_price
        )
        / price
    ) * 100

    maximum_safe_discount = max(
        0,
        maximum_safe_discount,
    )

    # =====================================================
    # APPROVED DISCOUNT
    # =====================================================

    approved_discount = min(
        requested_discount,
        merchant_max_discount,
        maximum_safe_discount,
    )

    approved_discount = max(
        0,
        approved_discount,
    )

    approved_discount = round(
        approved_discount,
        2,
    )

    # =====================================================
    # FINAL UNIT PRICE
    # =====================================================

    final_price = (
        price
        * (
            1
            - approved_discount / 100
        )
    )

    final_price = round(
        final_price,
        2,
    )

    if final_price <= 0:
        raise ValueError(
            "Final price must be greater than zero"
        )

    # =====================================================
    # FINAL MARGIN
    # =====================================================

    final_margin = (
        (
            final_price
            - cost_price
        )
        / final_price
    ) * 100

    final_margin = round(
        final_margin,
        2,
    )

    # =====================================================
    # ORDER AMOUNTS
    # =====================================================

    original_amount = round(
        price * quantity,
        2,
    )

    final_amount = round(
        final_price * quantity,
        2,
    )

    discount_amount = round(
        original_amount
        - final_amount,
        2,
    )

    # =====================================================
    # DISCOUNT ADJUSTMENT
    # =====================================================

    discount_adjusted = (
        requested_discount
        > approved_discount
    )

    # =====================================================
    # STORE DECISION
    # =====================================================

    state[
        "maximum_safe_discount_percent"
    ] = round(
        maximum_safe_discount,
        2,
    )

    state[
        "approved_discount_percent"
    ] = approved_discount

    state["final_price"] = final_price

    state[
        "final_margin_percent"
    ] = final_margin

    state["original_amount"] = (
        original_amount
    )

    state["discount_amount"] = (
        discount_amount
    )

    state["final_amount"] = (
        final_amount
    )

    state["discount_adjusted"] = (
        discount_adjusted
    )

    state["approved"] = True

    # =====================================================
    # EXPLANATION
    # =====================================================

    if discount_adjusted:

        state[
            "decision_explanation"
        ] = (
            f"Requested discount of "
            f"{requested_discount:.2f}% "
            f"was adjusted to "
            f"{approved_discount:.2f}%. "
            f"The approved discount is within "
            f"merchant policy and minimum "
            f"margin requirements."
        )

    else:

        state[
            "decision_explanation"
        ] = (
            f"Requested discount of "
            f"{requested_discount:.2f}% "
            f"is within merchant policy "
            f"and minimum margin requirements."
        )

    return state


# =========================================================
# RISK AGENT
# =========================================================
#
# IMPORTANT CHANGE:
#
# Large quantity now produces progressively higher risk.
#
# Quantity:
#
#   1 - 4     -> 0
#   5 - 9     -> 10
#   10 - 19   -> 25
#   20 - 29   -> 40
#   30 - 49   -> 50
#   50+       -> 60
#
# Discount:
#
#   10%+      -> 10
#   20%+      -> 25
#   30%+      -> 35
#
# Payment:
#
#   Above limit -> 20
#
# Discount adjustment:
#
#   +10
#
# This allows genuine HIGH / CRITICAL test orders.
#
# =========================================================

def risk_agent(
    state: PayPilotState,
) -> PayPilotState:

    risk_score = 0.0

    risk_reasons: list[str] = []

    quantity = int(
        state["quantity"]
    )

    final_amount = float(
        state["final_amount"]
    )

    payment_limit = float(
        state["auto_payment_limit"]
    )

    stock_quantity = int(
        state["stock_quantity"]
    )

    requested_discount = float(
        state.get(
            "requested_discount_percent",
            0,
        )
    )

    approved_discount = float(
        state["approved_discount_percent"]
    )

    # =====================================================
    # QUANTITY RISK
    # =====================================================

    if quantity >= 50:

        risk_score += 60

        risk_reasons.append(
            "Extremely large order quantity."
        )

    elif quantity >= 30:

        risk_score += 50

        risk_reasons.append(
            "Very high order quantity."
        )

    elif quantity >= 20:

        risk_score += 40

        risk_reasons.append(
            "Unusually large order quantity."
        )

    elif quantity >= 10:

        risk_score += 25

        risk_reasons.append(
            "High order quantity."
        )

    elif quantity >= 5:

        risk_score += 10

        risk_reasons.append(
            "Above-normal order quantity."
        )

    # =====================================================
    # DISCOUNT RISK
    # =====================================================

    if requested_discount >= 30:

        risk_score += 35

        risk_reasons.append(
            "Very high discount percentage."
        )

    elif requested_discount >= 20:

        risk_score += 25

        risk_reasons.append(
            "High discount percentage."
        )

    elif requested_discount >= 10:

        risk_score += 10

        risk_reasons.append(
            "Elevated discount percentage."
        )

    # =====================================================
    # PAYMENT LIMIT RISK
    # =====================================================

    if final_amount > payment_limit:

        risk_score += 20

        risk_reasons.append(
            "Order amount exceeds automatic payment limit."
        )

    # =====================================================
    # DISCOUNT ADJUSTMENT
    # =====================================================

    if requested_discount > approved_discount:

        risk_score += 10

        risk_reasons.append(
            "Requested discount was adjusted by policy."
        )

    # =====================================================
    # STOCK
    # =====================================================

    if quantity > stock_quantity:

        risk_score += 25

        risk_reasons.append(
            "Requested quantity exceeds available stock."
        )

        state["stock_available"] = False

    else:

        state["stock_available"] = True

    # =====================================================
    # DEDUPLICATE
    # =====================================================

    risk_reasons = list(
        dict.fromkeys(
            risk_reasons
        )
    )

    # =====================================================
    # LIMIT SCORE
    # =====================================================

    risk_score = min(
        max(risk_score, 0),
        100,
    )

    # =====================================================
    # RISK LEVEL
    # =====================================================

    if risk_score >= 80:

        risk_level = "CRITICAL"

    elif risk_score >= 60:

        risk_level = "HIGH"

    elif risk_score >= 30:

        risk_level = "MEDIUM"

    else:

        risk_level = "LOW"

    # =====================================================
    # MANUAL REVIEW
    # =====================================================

    manual_review_required = False

    if risk_level in {
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    }:

        manual_review_required = True

    if final_amount > payment_limit:

        manual_review_required = True

    if quantity >= 10:

        manual_review_required = True

    if quantity > stock_quantity:

        manual_review_required = True

    # =====================================================
    # STORE RISK
    # =====================================================

    state["risk_score"] = round(
        risk_score,
        2,
    )

    state["risk_level"] = (
        risk_level
    )

    state["risk_reasons"] = (
        risk_reasons
    )

    state[
        "manual_review_required"
    ] = manual_review_required

    # =====================================================
    # RISK EXPLANATION
    # =====================================================

    if risk_reasons:

        state[
            "risk_explanation"
        ] = (
            "Risk was calculated from: "
            + " ".join(
                risk_reasons
            )
        )

    else:

        state[
            "risk_explanation"
        ] = (
            "No significant risk factors detected."
        )

    return state


# =========================================================
# PAYMENT AGENT
# =========================================================
#
# IMPORTANT:
#
# HIGH / CRITICAL does NOT mean automatic inventory
# rejection.
#
# If stock exists:
#
#       HIGH/CRITICAL
#             |
#             v
#       MANUAL REVIEW
#             |
#        APPROVE
#             |
#             v
#          PAYMENT
#
# If stock does not exist:
#
#       ANY RISK
#          |
#          v
#      HARD BLOCK
#
# =========================================================

def payment_agent(
    state: PayPilotState,
) -> PayPilotState:

    payment_amount = float(
        state["final_amount"]
    )

    payment_limit = float(
        state["auto_payment_limit"]
    )

    risk_level = str(
        state.get(
            "risk_level",
            "HIGH",
        )
    ).upper()

    manual_review_required = bool(
        state.get(
            "manual_review_required",
            False,
        )
    )

    manual_review_decision = str(
        state.get(
            "manual_review_decision",
            "",
        )
    ).upper()

    policy_loaded = bool(
        state.get(
            "policy_loaded",
            False,
        )
    )

    product_active = bool(
        state.get(
            "product_active",
            False,
        )
    )

    merchant_active = bool(
        state.get(
            "merchant_active",
            False,
        )
    )

    stock_quantity = int(
        state.get(
            "stock_quantity",
            0,
        )
    )

    quantity = int(
        state.get(
            "quantity",
            0,
        )
    )

    # =====================================================
    # PAYMENT INFORMATION
    # =====================================================

    state["payment_required"] = True

    state["payment_amount"] = (
        payment_amount
    )

    hard_block_reasons: list[str] = []

    review_reasons: list[str] = []

    # =====================================================
    # POLICY
    # =====================================================

    if not policy_loaded:

        hard_block_reasons.append(
            "Merchant policy was not loaded."
        )

    # =====================================================
    # MERCHANT
    # =====================================================

    if not merchant_active:

        hard_block_reasons.append(
            "Merchant is inactive."
        )

    # =====================================================
    # PRODUCT
    # =====================================================

    if not product_active:

        hard_block_reasons.append(
            "Product is inactive."
        )

    # =====================================================
    # INVALID PAYMENT
    # =====================================================

    if payment_amount <= 0:

        hard_block_reasons.append(
            "Payment amount must be greater than zero."
        )

    # =====================================================
    # PAYMENT LIMIT
    # =====================================================

    if payment_amount > payment_limit:

        review_reasons.append(
            "Payment amount exceeds automatic payment limit."
        )

    # =====================================================
    # RISK
    # =====================================================

    if risk_level == "MEDIUM":

        review_reasons.append(
            "Risk level is MEDIUM."
        )

    elif risk_level == "HIGH":

        review_reasons.append(
            "Risk level is HIGH."
        )

    elif risk_level == "CRITICAL":

        review_reasons.append(
            "Risk level is CRITICAL."
        )

    # =====================================================
    # STOCK
    # =====================================================
    #
    # THIS IS THE ONLY LARGE-QUANTITY SAFETY BLOCK.
    #
    # A quantity of 100 is allowed if stock = 200.
    #
    # A quantity of 100 is blocked if stock = 50.
    #
    # =====================================================

    if quantity <= 0:

        hard_block_reasons.append(
            "Quantity must be greater than zero."
        )

        state["stock_available"] = False

    elif quantity > stock_quantity:

        hard_block_reasons.append(
            "Insufficient stock. "
            f"Requested: {quantity}, "
            f"Available: {stock_quantity}."
        )

        state["stock_available"] = False

    else:

        state["stock_available"] = True

    # =====================================================
    # MANUAL REVIEW
    # =====================================================

    if manual_review_required:

        review_reasons.append(
            "Manual review is required."
        )

    # =====================================================
    # DEDUPLICATE
    # =====================================================

    hard_block_reasons = list(
        dict.fromkeys(
            hard_block_reasons
        )
    )

    review_reasons = list(
        dict.fromkeys(
            review_reasons
        )
    )

    state[
        "hard_block_reasons"
    ] = hard_block_reasons

    state[
        "review_reasons"
    ] = review_reasons

    # =====================================================
    # HARD BLOCK
    # =====================================================

    if hard_block_reasons:

        state["payment_approved"] = False

        state[
            "manual_review_required"
        ] = True

        state[
            "payment_gate_status"
        ] = "BLOCKED"

        state[
            "payment_gate_reason"
        ] = " ".join(
            hard_block_reasons
        )

        return state

    # =====================================================
    # MANUAL APPROVAL
    # =====================================================

    if manual_review_decision == "APPROVE":

        state["payment_approved"] = True

        state[
            "manual_review_required"
        ] = False

        state[
            "payment_gate_status"
        ] = "APPROVED_BY_MANUAL_REVIEW"

        state[
            "payment_gate_reason"
        ] = (
            "Manual reviewer approved the order "
            "after risk and payment review. "
            "All hard safety gates passed."
        )

        return state

    # =====================================================
    # MANUAL REJECTION
    # =====================================================

    if manual_review_decision == "REJECT":

        state["payment_approved"] = False

        state[
            "manual_review_required"
        ] = False

        state[
            "payment_gate_status"
        ] = "REJECTED_BY_MANUAL_REVIEW"

        state[
            "payment_gate_reason"
        ] = (
            "Manual reviewer rejected the order."
        )

        return state

    # =====================================================
    # AUTOMATIC REVIEW BLOCK
    # =====================================================

    if review_reasons:

        state["payment_approved"] = False

        state[
            "manual_review_required"
        ] = True

        state[
            "payment_gate_status"
        ] = "BLOCKED"

        state[
            "payment_gate_reason"
        ] = " ".join(
            review_reasons
        )

        return state

    # =====================================================
    # AUTOMATIC APPROVAL
    # =====================================================

    state["payment_approved"] = True

    state[
        "payment_gate_status"
    ] = "APPROVED"

    state[
        "payment_gate_reason"
    ] = (
        "Payment passed all automatic payment gates."
    )

    return state


# =========================================================
# AUDIT AGENT
# =========================================================

def audit_agent(
    state: PayPilotState,
) -> PayPilotState:

    payment_approved = bool(
        state.get(
            "payment_approved",
            False,
        )
    )

    manual_review_required = bool(
        state.get(
            "manual_review_required",
            False,
        )
    )

    discount_adjusted = bool(
        state.get(
            "discount_adjusted",
            False,
        )
    )

    risk_level = str(
        state.get(
            "risk_level",
            "LOW",
        )
    ).upper()

    risk_score = float(
        state.get(
            "risk_score",
            0,
        )
    )

    manual_review_decision = str(
        state.get(
            "manual_review_decision",
            "",
        )
    ).upper()

    payment_gate_status = str(
        state.get(
            "payment_gate_status",
            "UNKNOWN",
        )
    )

    # =====================================================
    # FINAL STATUS
    # =====================================================

    if payment_approved:

        status = "APPROVED"

        if (
            manual_review_decision
            == "APPROVE"
        ):

            message = (
                "Order manually approved successfully "
                "after passing all hard safety gates."
            )

        elif discount_adjusted:

            message = (
                "Order approved with a "
                "policy-adjusted discount."
            )

        else:

            message = (
                "Order approved successfully."
            )

    else:

        if (
            manual_review_decision
            == "REJECT"
        ):

            status = "REJECTED"

            message = (
                "Order rejected during manual review."
            )

        else:

            status = (
                "MANUAL_REVIEW_REQUIRED"
            )

            message = (
                "Order requires manual review "
                "before payment can proceed."
            )

    # =====================================================
    # AUDIT EXPLANATION
    # =====================================================

    audit_parts: list[str] = []

    decision_explanation = state.get(
        "decision_explanation"
    )

    risk_explanation = state.get(
        "risk_explanation"
    )

    payment_gate_reason = state.get(
        "payment_gate_reason"
    )

    if decision_explanation:

        audit_parts.append(
            str(
                decision_explanation
            )
        )

    if risk_explanation:

        audit_parts.append(
            str(
                risk_explanation
            )
        )

    if payment_gate_reason:

        audit_parts.append(
            "Payment gate: "
            + str(
                payment_gate_reason
            )
        )

    audit_message = message

    if audit_parts:

        audit_message += (
            " "
            + " ".join(
                audit_parts
            )
        )

    # =====================================================
    # FINAL STATE
    # =====================================================

    state["status"] = status

    state["message"] = message

    state["audit_message"] = (
        audit_message
    )

    state["audit_event_type"] = (
        "ORDER_DECISION"
    )

    state["audit_old_status"] = (
        "NEW"
    )

    state["audit_new_status"] = (
        status
    )

    state["audit_performed_by"] = (
        "PAYPILOT_AI_AGENT"
    )

    state["final_explanation"] = (
        audit_message
    )

    # =====================================================
    # AUDIT SNAPSHOT
    # =====================================================

    state["audit_snapshot"] = {

        "status": status,

        "risk_score": round(
            risk_score,
            2,
        ),

        "risk_level": risk_level,

        "risk_reasons": state.get(
            "risk_reasons",
            [],
        ),

        "requested_discount_percent": (
            state.get(
                "requested_discount_percent",
                0,
            )
        ),

        "approved_discount_percent": (
            state.get(
                "approved_discount_percent",
                0,
            )
        ),

        "final_amount": state.get(
            "final_amount",
            0,
        ),

        "payment_approved": (
            payment_approved
        ),

        "manual_review_required": (
            manual_review_required
        ),

        "manual_review_decision": (
            manual_review_decision
        ),

        "payment_gate_status": (
            payment_gate_status
        ),

        "payment_gate_reason": (
            state.get(
                "payment_gate_reason",
                "",
            )
        ),

        "stock_available": state.get(
            "stock_available",
            None,
        ),

        "hard_block_reasons": state.get(
            "hard_block_reasons",
            [],
        ),

        "review_reasons": state.get(
            "review_reasons",
            [],
        ),
    }

    return state