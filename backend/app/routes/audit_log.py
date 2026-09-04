from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.audit_log import AuditLog


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


# =========================================================
# GET AUDIT LOGS
# =========================================================

@router.get("/")
def get_audit_logs(
    order_id: Optional[int] = Query(default=None),
    merchant_id: Optional[int] = Query(default=None),
    payment_id: Optional[int] = Query(default=None),

    # Frontend search box
    search: Optional[str] = Query(default=None),

    # Event filter
    event_type: Optional[str] = Query(default=None),

    # Campaign filter
    campaign_id: Optional[int] = Query(default=None),

    # Risk filter
    risk_level: Optional[str] = Query(default=None),

    # Performed by filter
    performed_by: Optional[str] = Query(default=None),

    skip: int = Query(
        default=0,
        ge=0,
    ),

    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),

    db: Session = Depends(get_db),
):
    """
    Get audit logs.

    Supported filters:

        order_id
        merchant_id
        payment_id
        search
        event_type
        campaign_id
        risk_level
        performed_by

    Results are returned newest first.
    """

    query = db.query(AuditLog)

    # =====================================================
    # ORDER FILTER
    # =====================================================

    if order_id is not None:
        query = query.filter(
            AuditLog.order_id == order_id
        )

    # =====================================================
    # MERCHANT FILTER
    # =====================================================

    if merchant_id is not None:
        query = query.filter(
            AuditLog.merchant_id == merchant_id
        )

    # =====================================================
    # PAYMENT FILTER
    # =====================================================

    if payment_id is not None:
        query = query.filter(
            AuditLog.payment_id == payment_id
        )

    # =====================================================
    # SEARCH
    # =====================================================
    #
    # IMPORTANT:
    #
    # The Audit Logs frontend search box can contain:
    #
    #   Gaming Revenue Safe Discount
    #   Gaming Revenue Boost
    #   Razorpay
    #   Payment
    #   Campaign
    #   Manual review
    #
    # Search across the fields that exist in AuditLog.
    #
    # =====================================================

    if search and search.strip():

        search_value = search.strip()

        search_pattern = f"%{search_value}%"

        query = query.filter(
            or_(
                AuditLog.event_type.ilike(
                    search_pattern
                ),

                AuditLog.performed_by.ilike(
                    search_pattern
                ),

                AuditLog.message.ilike(
                    search_pattern
                ),
            )
        )

    # =====================================================
    # EVENT TYPE FILTER
    # =====================================================

    if event_type and event_type.strip():

        normalized_event = (
            event_type
            .strip()
            .upper()
            .replace("-", "_")
            .replace(" ", "_")
        )

        # -------------------------------------------------
        # Frontend:
        #
        # "All Events"
        # -------------------------------------------------

        if normalized_event in {
            "",
            "ALL",
            "ALL_EVENTS",
        }:
            pass

        # -------------------------------------------------
        # Order Decision
        # -------------------------------------------------

        elif normalized_event in {
            "ORDER_DECISION",
            "ORDER",
        }:

            query = query.filter(
                AuditLog.event_type.ilike(
                    "ORDER_DECISION%"
                )
            )

        # -------------------------------------------------
        # Manual Review
        # -------------------------------------------------

        elif normalized_event in {
            "MANUAL_REVIEW",
            "MANUAL_REVIEW_DECISION",
        }:

            query = query.filter(
                AuditLog.event_type.ilike(
                    "MANUAL_REVIEW%"
                )
            )

        # -------------------------------------------------
        # Campaign
        # -------------------------------------------------

        elif normalized_event in {
            "CAMPAIGN",
            "CAMPAIGN_ORCHESTRATOR",
        }:

            query = query.filter(
                AuditLog.event_type.ilike(
                    "CAMPAIGN%"
                )
            )

        # -------------------------------------------------
        # Payment
        # -------------------------------------------------

        elif normalized_event == "PAYMENT":

            query = query.filter(
                AuditLog.event_type.ilike(
                    "PAYMENT%"
                )
            )

        # -------------------------------------------------
        # Exact event type
        # -------------------------------------------------

        else:

            query = query.filter(
                AuditLog.event_type.ilike(
                    event_type.strip()
                )
            )

    # =====================================================
    # CAMPAIGN FILTER
    # =====================================================
    #
    # The current AuditLog model does not require a
    # campaign_id database column.
    #
    # Campaign information can be found in event_type
    # and message.
    #
    # =====================================================

    if campaign_id is not None:

        campaign_id_text = str(campaign_id)

        campaign_pattern = (
            f"%{campaign_id_text}%"
        )

        query = query.filter(
            or_(
                AuditLog.event_type.ilike(
                    campaign_pattern
                ),

                AuditLog.message.ilike(
                    campaign_pattern
                ),
            )
        )

    # =====================================================
    # RISK FILTER
    # =====================================================

    if risk_level and risk_level.strip():

        normalized_risk = (
            risk_level
            .strip()
            .upper()
        )

        if normalized_risk not in {
            "ALL",
            "ALL_RISK",
        }:

            query = query.filter(
                AuditLog.risk_level.ilike(
                    risk_level.strip()
                )
            )

    # =====================================================
    # PERFORMED BY FILTER
    # =====================================================

    if performed_by and performed_by.strip():

        query = query.filter(
            AuditLog.performed_by.ilike(
                performed_by.strip()
            )
        )

    # =====================================================
    # COUNT
    # =====================================================

    total = query.count()

    # =====================================================
    # ORDER
    # =====================================================

    logs = (
        query
        .order_by(
            AuditLog.created_at.desc(),
            AuditLog.id.desc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    # =====================================================
    # RESPONSE
    # =====================================================

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "logs": logs,
    }


# =========================================================
# GET AUDIT LOGS FOR ONE ORDER
# =========================================================

@router.get("/order/{order_id}")
def get_order_audit_logs(
    order_id: int,
    db: Session = Depends(get_db),
):
    """
    Return the complete audit history for one order.

    Newest event appears first.
    """

    logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.order_id == order_id
        )
        .order_by(
            AuditLog.created_at.desc(),
            AuditLog.id.desc(),
        )
        .all()
    )

    return {
        "order_id": order_id,
        "total": len(logs),
        "logs": logs,
    }


# =========================================================
# GET PAYMENT AUDIT LOGS
# =========================================================

@router.get("/payment/{payment_id}")
def get_payment_audit_logs(
    payment_id: int,
    db: Session = Depends(get_db),
):
    """
    Return audit history for one payment.

    Useful for checking the payment lifecycle
    independently from the order decision lifecycle.
    """

    logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.payment_id == payment_id
        )
        .order_by(
            AuditLog.created_at.desc(),
            AuditLog.id.desc(),
        )
        .all()
    )

    return {
        "payment_id": payment_id,
        "total": len(logs),
        "logs": logs,
    }


# =========================================================
# GET CAMPAIGN AUDIT LOGS
# =========================================================

@router.get("/campaign/{campaign_id}")
def get_campaign_audit_logs(
    campaign_id: int,
    merchant_id: Optional[int] = Query(
        default=None
    ),
    db: Session = Depends(get_db),
):
    """
    Return audit history for one campaign.

    Campaign events can be represented through:
        event_type
        message

    No campaign_id column is required in AuditLog.
    """

    campaign_text = str(campaign_id)

    campaign_pattern = (
        f"%{campaign_text}%"
    )

    query = (
        db.query(AuditLog)
        .filter(
            or_(
                AuditLog.event_type.ilike(
                    campaign_pattern
                ),
                AuditLog.message.ilike(
                    campaign_pattern
                ),
            )
        )
    )

    # -----------------------------------------------------
    # MERCHANT FILTER
    # -----------------------------------------------------

    if merchant_id is not None:

        query = query.filter(
            AuditLog.merchant_id == merchant_id
        )

    # -----------------------------------------------------
    # SORT
    # -----------------------------------------------------

    logs = (
        query
        .order_by(
            AuditLog.created_at.asc(),
            AuditLog.id.asc(),
        )
        .all()
    )

    return {
        "campaign_id": campaign_id,
        "merchant_id": merchant_id,
        "total": len(logs),
        "logs": logs,
    }


# =========================================================
# AUDIT LOG SUMMARY
# =========================================================
#
# IMPORTANT:
# This route MUST be declared before /{log_id}.
# =========================================================

@router.get("/summary/stats")
def get_audit_log_summary(
    db: Session = Depends(get_db),
):
    """
    Get audit log statistics.
    """

    # =====================================================
    # TOTAL LOGS
    # =====================================================

    total_logs = (
        db.query(AuditLog)
        .count()
    )

    # =====================================================
    # MANUAL REVIEW DECISIONS
    # =====================================================

    manual_review_decisions = (
        db.query(AuditLog)
        .filter(
            AuditLog.event_type.ilike(
                "MANUAL_REVIEW%"
            )
        )
        .count()
    )

    # =====================================================
    # APPROVED
    # =====================================================

    approved_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.new_status == "APPROVED"
        )
        .count()
    )

    # =====================================================
    # REJECTED
    # =====================================================

    rejected_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.new_status == "REJECTED"
        )
        .count()
    )

    # =====================================================
    # PAYMENT CAPTURED
    # =====================================================

    captured_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.event_type
            == "PAYMENT_CAPTURED"
        )
        .count()
    )

    # =====================================================
    # PAYMENT REFUNDED
    # =====================================================

    refunded_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.event_type
            == "PAYMENT_REFUNDED"
        )
        .count()
    )

    # =====================================================
    # CAMPAIGN EVENTS
    # =====================================================

    campaign_events = (
        db.query(AuditLog)
        .filter(
            AuditLog.event_type.ilike(
                "CAMPAIGN%"
            )
        )
        .count()
    )

    # =====================================================
    # CAMPAIGN PROPOSALS
    # =====================================================

    campaign_proposals = (
        db.query(AuditLog)
        .filter(
            AuditLog.event_type.ilike(
                "CAMPAIGN_PROPOSAL_CREATED%"
            )
        )
        .count()
    )

    # =====================================================
    # CAMPAIGN POLICY VALIDATED
    # =====================================================

    campaign_policy_validated = (
        db.query(AuditLog)
        .filter(
            AuditLog.event_type.ilike(
                "CAMPAIGN_POLICY_VALIDATED%"
            )
        )
        .count()
    )

    # =====================================================
    # CAMPAIGN POLICY REJECTED
    # =====================================================

    campaign_policy_rejected = (
        db.query(AuditLog)
        .filter(
            AuditLog.event_type.ilike(
                "CAMPAIGN_POLICY_REJECTED%"
            )
        )
        .count()
    )

    # =====================================================
    # CAMPAIGN MERCHANT APPROVED
    # =====================================================

    campaign_merchant_approved = (
        db.query(AuditLog)
        .filter(
            AuditLog.event_type.ilike(
                "CAMPAIGN_MERCHANT_APPROVED%"
            )
        )
        .count()
    )

    # =====================================================
    # CAMPAIGN MERCHANT REJECTED
    # =====================================================

    campaign_merchant_rejected = (
        db.query(AuditLog)
        .filter(
            AuditLog.event_type.ilike(
                "CAMPAIGN_MERCHANT_REJECTED%"
            )
        )
        .count()
    )

    # =====================================================
    # CAMPAIGN ACTIVATED
    # =====================================================

    campaign_activated = (
        db.query(AuditLog)
        .filter(
            AuditLog.event_type.ilike(
                "CAMPAIGN_ACTIVATED%"
            )
        )
        .count()
    )

    # =====================================================
    # RESPONSE
    # =====================================================

    return {
        "total_logs": total_logs,

        "manual_review_decisions": (
            manual_review_decisions
        ),

        "approved": approved_logs,

        "rejected": rejected_logs,

        "payment_captured": (
            captured_logs
        ),

        "payment_refunded": (
            refunded_logs
        ),

        # Campaign statistics
        "campaign_events": (
            campaign_events
        ),

        "campaign_proposals": (
            campaign_proposals
        ),

        "campaign_policy_validated": (
            campaign_policy_validated
        ),

        "campaign_policy_rejected": (
            campaign_policy_rejected
        ),

        "campaign_merchant_approved": (
            campaign_merchant_approved
        ),

        "campaign_merchant_rejected": (
            campaign_merchant_rejected
        ),

        "campaign_activated": (
            campaign_activated
        ),
    }


# =========================================================
# GET SINGLE AUDIT LOG
# =========================================================
#
# IMPORTANT:
# Keep this route LAST.
#
# Otherwise:
#
# /summary/stats
# /campaign/5
# /order/214
# /payment/61
#
# can be interpreted incorrectly as {log_id}.
# =========================================================

@router.get("/{log_id}")
def get_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
):
    """
    Get one audit log by ID.
    """

    log = (
        db.query(AuditLog)
        .filter(
            AuditLog.id == log_id
        )
        .first()
    )

    if not log:

        raise HTTPException(
            status_code=404,
            detail="Audit log not found",
        )

    return log