from typing import TypedDict, Optional, List, Dict, Any


class PayPilotState(TypedDict, total=False):

    # =========================================================
    # ORDER INPUT
    # =========================================================

    order_id: int

    merchant_id: int
    product_id: int

    quantity: int

    requested_discount_percent: float

    # =========================================================
    # PRODUCT INFORMATION
    # =========================================================

    product_name: str

    original_price: float
    cost_price: float

    stock_quantity: int

    # Quantity requested by customer
    requested_quantity: int

    # Quantity confirmed/available during workflow
    available_stock: int

    # =========================================================
    # INVENTORY STATE
    # =========================================================

    stock_check_passed: bool

    stock_reserved: bool

    stock_deducted: bool

    stock_error: str

    inventory_status: str

    # Possible values:
    #
    # AVAILABLE
    # INSUFFICIENT_STOCK
    # RESERVED
    # DEDUCTED
    # RELEASED
    # FAILED

    # =========================================================
    # PRODUCT STATUS
    # =========================================================

    product_active: bool

    # =========================================================
    # MERCHANT INFORMATION
    # =========================================================

    merchant_name: str

    merchant_active: bool

    # =========================================================
    # MERCHANT POLICY
    # =========================================================

    maximum_discount_percent: float

    minimum_margin: float

    auto_payment_limit: float

    bundle_allowed: bool

    # =========================================================
    # POLICY STATUS
    # =========================================================

    policy_loaded: bool

    policy_allowed: bool

    policy_reason: str

    policy_explanation: str

    # =========================================================
    # DECISION AGENT
    # =========================================================

    maximum_safe_discount_percent: float

    approved_discount_percent: float

    final_price: float

    final_margin_percent: float

    original_amount: float

    discount_amount: float

    final_amount: float

    approved: bool

    discount_adjusted: bool

    decision_explanation: str

    # Compatibility field
    decision_reason: str

    # =========================================================
    # RISK AGENT
    # =========================================================

    risk_score: float

    risk_level: str

    risk_reasons: List[str]

    risk_explanation: str

    # Structured risk factors
    risk_factors: List[Dict[str, Any]]

    manual_review_required: bool

    # =========================================================
    # PAYMENT AGENT
    # =========================================================

    payment_required: bool

    payment_amount: float

    payment_approved: bool

    payment_gate_status: str

    payment_gate_reason: str

    # =========================================================
    # MANUAL REVIEW
    # =========================================================
    #
    # These fields are important because the AI decision
    # and the human review decision are different events.
    #
    # AI:
    #   MANUAL_REVIEW_REQUIRED
    #
    # Human:
    #   APPROVE / REJECT
    #
    # =========================================================

    manual_review_id: int

    manual_review_status: str

    # Possible values:
    #
    # PENDING
    # APPROVED
    # REJECTED

    manual_review_action: str

    # APPROVE / REJECT

    reviewed_by: str

    review_comment: str

    review_completed: bool

    review_error: str

    # =========================================================
    # POST-REVIEW DECISION
    # =========================================================

    final_decision: str

    # Possible values:
    #
    # APPROVED
    # REJECTED
    # MANUAL_REVIEW_REQUIRED

    final_decision_reason: str

    # =========================================================
    # AUDIT AGENT
    # =========================================================

    audit_event_type: str

    audit_message: str

    audit_old_status: str

    audit_new_status: str

    audit_performed_by: str

    audit_snapshot: Dict[str, Any]

    # =========================================================
    # AUDIT TRAIL
    # =========================================================

    audit_events: List[Dict[str, Any]]

    # =========================================================
    # FINAL WORKFLOW RESULT
    # =========================================================

    status: str

    message: str

    # =========================================================
    # AI EXPLANATION
    # =========================================================

    # Structured explanation generated by AIService
    explanation: Dict[str, Any]

    # Final human-readable explanation
    final_explanation: str