from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from app.agents.graph.state import PayPilotState

from app.agents.graph.nodes import (
    policy_agent,
    decision_agent,
    risk_agent,
    payment_agent,
    audit_agent,
)


# =========================================================
# PAYPILOT WORKFLOW
# =========================================================
#
# Complete PayPilot decision pipeline:
#
#       START
#         |
#         v
#   POLICY AGENT
#         |
#         v
#  DECISION AGENT
#         |
#         v
#    RISK AGENT
#         |
#         v
#   PAYMENT GATE
#         |
#         v
#    AUDIT AGENT
#         |
#         v
#        END
#
#
# Responsibilities
# ---------------------------------------------------------
#
# POLICY AGENT
#   - Merchant validation
#   - Product validation
#   - Product stock
#   - Merchant policy
#   - Maximum discount
#   - Minimum margin
#   - Automatic payment limit
#
# DECISION AGENT
#   - Original price
#   - Approved discount
#   - Final price
#   - Final margin
#   - Pricing decision
#
# RISK AGENT
#   - Risk score
#   - Risk level
#   - Risk reasons
#   - Risk factors
#   - Manual review requirement
#
# PAYMENT AGENT
#   - Hard safety gates
#   - Risk gates
#   - Automatic payment limit
#   - Payment approval/rejection
#
# AUDIT AGENT
#   - Final decision message
#   - Audit event information
#   - Explanation information
#
#
# IMPORTANT
# ---------------------------------------------------------
#
# This workflow DOES NOT:
#
#   - Create Order records
#   - Create ManualReview records
#   - Create AuditLog records
#   - Deduct inventory
#   - Restore inventory
#   - Create Razorpay payments
#   - Capture Razorpay payments
#   - Refund payments
#
# Database mutations remain in the service/routes layer.
#
# =========================================================


def build_paypilot_workflow(db):
    """
    Build and compile the PayPilot AI decision workflow.

    Pipeline:

        Policy
          ↓
        Decision
          ↓
        Risk
          ↓
        Payment Gate
          ↓
        Audit

    Only policy_agent receives the SQLAlchemy database
    session because policy/product/merchant information
    is loaded from the database there.
    """

    # =====================================================
    # 1. CREATE STATE GRAPH
    # =====================================================

    workflow = StateGraph(PayPilotState)

    # =====================================================
    # 2. POLICY AGENT
    # =====================================================

    def policy_node(state: PayPilotState) -> PayPilotState:
        """
        Wrapper around policy_agent.

        The database session is injected here.
        """

        return policy_agent(
            state,
            db,
        )

    workflow.add_node(
        "policy_agent",
        policy_node,
    )

    # =====================================================
    # 3. DECISION AGENT
    # =====================================================

    workflow.add_node(
        "decision_agent",
        decision_agent,
    )

    # =====================================================
    # 4. RISK AGENT
    # =====================================================
    #
    # IMPORTANT:
    #
    # All risk scoring should happen inside risk_agent.
    #
    # Expected output:
    #
    #   risk_score
    #   risk_level
    #   risk_reasons
    #   risk_factors
    #
    # Risk thresholds:
    #
    #   0  - 29   LOW
    #   30 - 59   MEDIUM
    #   60 - 79   HIGH
    #   80 - 100  CRITICAL
    #
    # =====================================================

    workflow.add_node(
        "risk_agent",
        risk_agent,
    )

    # =====================================================
    # 5. PAYMENT AGENT
    # =====================================================
    #
    # This is the PayPilot payment gate.
    #
    # It is NOT Razorpay.
    #
    # It determines whether the order can proceed
    # to actual payment.
    #
    # HARD BLOCKS:
    #
    #   - Invalid merchant
    #   - Invalid product
    #   - Inactive merchant
    #   - Inactive product
    #   - Missing policy
    #   - Insufficient stock
    #
    # REVIEW GATES:
    #
    #   - MEDIUM risk
    #   - HIGH risk
    #   - CRITICAL risk
    #   - Amount above automatic payment limit
    #   - Manual review requirement
    #
    # =====================================================

    workflow.add_node(
        "payment_agent",
        payment_agent,
    )

    # =====================================================
    # 6. AUDIT AGENT
    # =====================================================
    #
    # Produces audit information only.
    #
    # It DOES NOT write to the database.
    #
    # =====================================================

    workflow.add_node(
        "audit_agent",
        audit_agent,
    )

    # =====================================================
    # 7. GRAPH EDGES
    # =====================================================

    # -----------------------------------------------------
    # START → POLICY
    # -----------------------------------------------------

    workflow.add_edge(
        START,
        "policy_agent",
    )

    # -----------------------------------------------------
    # POLICY → DECISION
    # -----------------------------------------------------

    workflow.add_edge(
        "policy_agent",
        "decision_agent",
    )

    # -----------------------------------------------------
    # DECISION → RISK
    # -----------------------------------------------------

    workflow.add_edge(
        "decision_agent",
        "risk_agent",
    )

    # -----------------------------------------------------
    # RISK → PAYMENT
    # -----------------------------------------------------

    workflow.add_edge(
        "risk_agent",
        "payment_agent",
    )

    # -----------------------------------------------------
    # PAYMENT → AUDIT
    # -----------------------------------------------------

    workflow.add_edge(
        "payment_agent",
        "audit_agent",
    )

    # -----------------------------------------------------
    # AUDIT → END
    # -----------------------------------------------------

    workflow.add_edge(
        "audit_agent",
        END,
    )

    # =====================================================
    # 8. COMPILE
    # =====================================================

    compiled_workflow = workflow.compile()

    return compiled_workflow