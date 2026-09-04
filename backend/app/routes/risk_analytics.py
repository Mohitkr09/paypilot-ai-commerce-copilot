from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.order import Order
from app.models.audit_log import AuditLog


router = APIRouter(
    prefix="/risk-analytics",
    tags=["Risk Analytics"],
)


# =========================================================
# HELPERS
# =========================================================

def normalize_status(value):
    """
    Normalize status values so comparisons are consistent.
    """
    return str(value or "").strip().upper()


def normalize_risk_level(value):
    """
    Normalize risk level values.
    """
    return str(value or "").strip().upper()


# =========================================================
# SUMMARY
# =========================================================

@router.get("/summary")
def get_risk_summary(
    merchant_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Return the main Risk Analytics dashboard statistics.
    """

    # -----------------------------------------------------
    # ORDERS
    # -----------------------------------------------------

    order_query = db.query(Order)

    if merchant_id is not None:
        order_query = order_query.filter(
            Order.merchant_id == merchant_id
        )

    orders = order_query.all()

    # -----------------------------------------------------
    # ORDER COUNTS
    # -----------------------------------------------------

    total_orders = len(orders)

    approved_orders = sum(
        1
        for order in orders
        if normalize_status(order.status) == "APPROVED"
    )

    rejected_orders = sum(
        1
        for order in orders
        if normalize_status(order.status) == "REJECTED"
    )

    manual_review_orders = sum(
        1
        for order in orders
        if normalize_status(order.status)
        == "MANUAL_REVIEW_REQUIRED"
    )

    discount_adjusted_orders = sum(
        1
        for order in orders
        if normalize_status(order.status)
        == "DISCOUNT_ADJUSTED"
    )

    # -----------------------------------------------------
    # ORDER RATES
    # -----------------------------------------------------

    approval_rate = (
        approved_orders / total_orders * 100
        if total_orders > 0
        else 0
    )

    rejection_rate = (
        rejected_orders / total_orders * 100
        if total_orders > 0
        else 0
    )

    manual_review_rate = (
        manual_review_orders / total_orders * 100
        if total_orders > 0
        else 0
    )

    # -----------------------------------------------------
    # FINANCIAL STATISTICS
    # -----------------------------------------------------

    total_order_value = sum(
        float(order.final_amount or 0)
        for order in orders
    )

    approved_value = sum(
        float(order.final_amount or 0)
        for order in orders
        if normalize_status(order.status) == "APPROVED"
    )

    rejected_value = sum(
        float(order.final_amount or 0)
        for order in orders
        if normalize_status(order.status) == "REJECTED"
    )

    average_order_value = (
        total_order_value / total_orders
        if total_orders > 0
        else 0
    )

    # -----------------------------------------------------
    # RISK AUDIT LOGS
    # -----------------------------------------------------

    risk_query = (
        db.query(AuditLog)
        .filter(
            AuditLog.event_type == "ORDER_DECISION"
        )
    )

    if merchant_id is not None:
        risk_query = risk_query.filter(
            AuditLog.merchant_id == merchant_id
        )

    risk_logs = risk_query.all()

    # -----------------------------------------------------
    # RISK SCORES
    # -----------------------------------------------------

    risk_scores = [
        float(log.risk_score)
        for log in risk_logs
        if log.risk_score is not None
    ]

    average_risk_score = (
        sum(risk_scores) / len(risk_scores)
        if risk_scores
        else 0
    )

    # -----------------------------------------------------
    # RISK LEVEL COUNTS
    # -----------------------------------------------------

    low_risk = sum(
        1
        for log in risk_logs
        if normalize_risk_level(log.risk_level) == "LOW"
    )

    medium_risk = sum(
        1
        for log in risk_logs
        if normalize_risk_level(log.risk_level) == "MEDIUM"
    )

    high_risk = sum(
        1
        for log in risk_logs
        if normalize_risk_level(log.risk_level) == "HIGH"
    )

    critical_risk = sum(
        1
        for log in risk_logs
        if normalize_risk_level(log.risk_level) == "CRITICAL"
    )

    high_risk_reviews = high_risk + critical_risk

    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    return {
        "orders": {
            "total": total_orders,
            "approved": approved_orders,
            "rejected": rejected_orders,
            "manual_review": manual_review_orders,
            "discount_adjusted": discount_adjusted_orders,
        },

        "rates": {
            "approval_rate": round(
                approval_rate,
                2,
            ),
            "rejection_rate": round(
                rejection_rate,
                2,
            ),
            "manual_review_rate": round(
                manual_review_rate,
                2,
            ),
        },

        "risk": {
            "low": low_risk,
            "medium": medium_risk,
            "high": high_risk,
            "critical": critical_risk,
            "high_risk_total": high_risk_reviews,
            "average_score": round(
                average_risk_score,
                2,
            ),
        },

        "financial": {
            "total_order_value": round(
                total_order_value,
                2,
            ),
            "approved_value": round(
                approved_value,
                2,
            ),
            "rejected_value": round(
                rejected_value,
                2,
            ),
            "average_order_value": round(
                average_order_value,
                2,
            ),
        },

        "reviews": {
            "total": len(risk_logs),
            "pending": manual_review_orders,
            "approved": approved_orders,
            "rejected": rejected_orders,
        },
    }


# =========================================================
# RISK DISTRIBUTION
# =========================================================

@router.get("/risk-distribution")
def get_risk_distribution(
    merchant_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Return LOW / MEDIUM / HIGH / CRITICAL risk distribution.
    """

    query = (
        db.query(
            AuditLog.risk_level,
            func.count(AuditLog.id),
        )
        .filter(
            AuditLog.event_type == "ORDER_DECISION"
        )
    )

    if merchant_id is not None:
        query = query.filter(
            AuditLog.merchant_id == merchant_id
        )

    results = (
        query
        .group_by(AuditLog.risk_level)
        .all()
    )

    distribution = {
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 0,
        "CRITICAL": 0,
    }

    for risk_level, count in results:

        normalized = normalize_risk_level(
            risk_level
        )

        if normalized in distribution:
            distribution[normalized] = count

    return {
        "distribution": distribution,
        "total": sum(
            distribution.values()
        ),
    }


# =========================================================
# STATUS DISTRIBUTION
# =========================================================

@router.get("/status-distribution")
def get_status_distribution(
    merchant_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Return order status distribution.
    """

    query = db.query(
        Order.status,
        func.count(Order.id),
    )

    if merchant_id is not None:
        query = query.filter(
            Order.merchant_id == merchant_id
        )

    results = (
        query
        .group_by(Order.status)
        .all()
    )

    distribution = {}

    for status, count in results:

        normalized = normalize_status(status)

        distribution[normalized] = count

    return {
        "distribution": distribution,
        "total": sum(
            distribution.values()
        ),
    }


# =========================================================
# RISK SCORE DISTRIBUTION
# =========================================================

@router.get("/risk-score-distribution")
def get_risk_score_distribution(
    merchant_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Return risk scores grouped into ranges.
    """

    query = (
        db.query(AuditLog)
        .filter(
            AuditLog.event_type == "ORDER_DECISION"
        )
    )

    if merchant_id is not None:
        query = query.filter(
            AuditLog.merchant_id == merchant_id
        )

    logs = query.all()

    ranges = {
        "0-20": 0,
        "21-40": 0,
        "41-60": 0,
        "61-80": 0,
        "81-100": 0,
    }

    for log in logs:

        if log.risk_score is None:
            continue

        score = float(log.risk_score)

        if score <= 20:
            ranges["0-20"] += 1

        elif score <= 40:
            ranges["21-40"] += 1

        elif score <= 60:
            ranges["41-60"] += 1

        elif score <= 80:
            ranges["61-80"] += 1

        else:
            ranges["81-100"] += 1

    return {
        "distribution": [
            {
                "range": key,
                "count": value,
            }
            for key, value in ranges.items()
        ]
    }


# =========================================================
# TOP RISK REASONS
# =========================================================

@router.get("/risk-reasons")
def get_risk_reasons(
    merchant_id: Optional[int] = Query(default=None),
    limit: int = Query(
        default=5,
        ge=1,
        le=20,
    ),
    db: Session = Depends(get_db),
):
    """
    Return the most common risk reasons.
    """

    query = (
        db.query(
            AuditLog.message,
            func.count(AuditLog.id),
        )
        .filter(
            AuditLog.event_type == "ORDER_DECISION"
        )
    )

    if merchant_id is not None:
        query = query.filter(
            AuditLog.merchant_id == merchant_id
        )

    results = (
        query
        .group_by(AuditLog.message)
        .order_by(
            func.count(AuditLog.id).desc()
        )
        .limit(limit)
        .all()
    )

    return {
        "reasons": [
            {
                "reason": message or "Unknown reason",
                "count": count,
            }
            for message, count in results
        ]
    }


# =========================================================
# RECENT RISK ACTIVITY
# =========================================================

@router.get("/recent")
def get_recent_risk_activity(
    merchant_id: Optional[int] = Query(default=None),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
):
    """
    Return the most recent audit/risk activity.
    """

    query = db.query(AuditLog)

    if merchant_id is not None:
        query = query.filter(
            AuditLog.merchant_id == merchant_id
        )

    logs = (
        query
        .order_by(
            AuditLog.created_at.desc()
        )
        .limit(limit)
        .all()
    )

    return {
        "count": len(logs),

        "activities": [
            {
                "id": log.id,
                "order_id": log.order_id,
                "merchant_id": log.merchant_id,
                "event_type": log.event_type,
                "message": log.message,
                "old_status": log.old_status,
                "new_status": log.new_status,
                "risk_score": log.risk_score,
                "risk_level": log.risk_level,
                "performed_by": log.performed_by,
                "created_at": log.created_at,
            }
            for log in logs
        ],
    }


# =========================================================
# DAILY ORDER TREND
# =========================================================

@router.get("/order-trend")
def get_order_trend(
    merchant_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Return daily order statistics for analytics charts.

    Uses Order.created_at.
    """

    query = db.query(Order)

    if merchant_id is not None:
        query = query.filter(
            Order.merchant_id == merchant_id
        )

    orders = (
        query
        .order_by(Order.created_at.asc())
        .all()
    )

    date_map = {}

    for order in orders:

        # -------------------------------------------------
        # ORDER DATE
        # -------------------------------------------------

        if order.created_at is None:
            continue

        order_date = order.created_at.date()

        date_string = order_date.isoformat()

        # -------------------------------------------------
        # CREATE DAILY BUCKET
        # -------------------------------------------------

        if date_string not in date_map:

            date_map[date_string] = {
                "date": date_string,
                "orders": 0,
                "approved": 0,
                "rejected": 0,
                "review": 0,
                "discount_adjusted": 0,
            }

        # -------------------------------------------------
        # TOTAL ORDERS
        # -------------------------------------------------

        date_map[date_string]["orders"] += 1

        # -------------------------------------------------
        # ORDER STATUS
        # -------------------------------------------------

        status = normalize_status(
            order.status
        )

        if status == "APPROVED":

            date_map[date_string]["approved"] += 1

        elif status == "REJECTED":

            date_map[date_string]["rejected"] += 1

        elif status == "MANUAL_REVIEW_REQUIRED":

            date_map[date_string]["review"] += 1

        elif status == "DISCOUNT_ADJUSTED":

            date_map[date_string][
                "discount_adjusted"
            ] += 1

    # -----------------------------------------------------
    # SORT CHRONOLOGICALLY
    # -----------------------------------------------------

    trend = sorted(
        date_map.values(),
        key=lambda item: item["date"],
    )

    return {
        "trend": trend
    }


# =========================================================
# MERCHANT ANALYTICS
# =========================================================

@router.get("/merchant/{merchant_id}")
def get_merchant_risk_analytics(
    merchant_id: int,
    db: Session = Depends(get_db),
):
    """
    Return complete risk analytics for one merchant.
    """

    orders = (
        db.query(Order)
        .filter(
            Order.merchant_id == merchant_id
        )
        .all()
    )

    risk_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.merchant_id == merchant_id,
            AuditLog.event_type == "ORDER_DECISION",
        )
        .all()
    )

    # -----------------------------------------------------
    # ORDER COUNTS
    # -----------------------------------------------------

    total_orders = len(orders)

    approved = sum(
        1
        for order in orders
        if normalize_status(order.status)
        == "APPROVED"
    )

    rejected = sum(
        1
        for order in orders
        if normalize_status(order.status)
        == "REJECTED"
    )

    manual_review = sum(
        1
        for order in orders
        if normalize_status(order.status)
        == "MANUAL_REVIEW_REQUIRED"
    )

    discount_adjusted = sum(
        1
        for order in orders
        if normalize_status(order.status)
        == "DISCOUNT_ADJUSTED"
    )

    # -----------------------------------------------------
    # RATES
    # -----------------------------------------------------

    approval_rate = (
        approved / total_orders * 100
        if total_orders > 0
        else 0
    )

    rejection_rate = (
        rejected / total_orders * 100
        if total_orders > 0
        else 0
    )

    manual_review_rate = (
        manual_review / total_orders * 100
        if total_orders > 0
        else 0
    )

    # -----------------------------------------------------
    # FINANCIAL
    # -----------------------------------------------------

    total_value = sum(
        float(order.final_amount or 0)
        for order in orders
    )

    approved_value = sum(
        float(order.final_amount or 0)
        for order in orders
        if normalize_status(order.status)
        == "APPROVED"
    )

    rejected_value = sum(
        float(order.final_amount or 0)
        for order in orders
        if normalize_status(order.status)
        == "REJECTED"
    )

    average_order_value = (
        total_value / total_orders
        if total_orders > 0
        else 0
    )

    # -----------------------------------------------------
    # RISK
    # -----------------------------------------------------

    risk_scores = [
        float(log.risk_score)
        for log in risk_logs
        if log.risk_score is not None
    ]

    average_risk_score = (
        sum(risk_scores) / len(risk_scores)
        if risk_scores
        else 0
    )

    low = sum(
        1
        for log in risk_logs
        if normalize_risk_level(
            log.risk_level
        ) == "LOW"
    )

    medium = sum(
        1
        for log in risk_logs
        if normalize_risk_level(
            log.risk_level
        ) == "MEDIUM"
    )

    high = sum(
        1
        for log in risk_logs
        if normalize_risk_level(
            log.risk_level
        ) == "HIGH"
    )

    critical = sum(
        1
        for log in risk_logs
        if normalize_risk_level(
            log.risk_level
        ) == "CRITICAL"
    )

    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    return {
        "merchant_id": merchant_id,

        "orders": {
            "total": total_orders,
            "approved": approved,
            "rejected": rejected,
            "manual_review": manual_review,
            "discount_adjusted": discount_adjusted,
        },

        "rates": {
            "approval_rate": round(
                approval_rate,
                2,
            ),
            "rejection_rate": round(
                rejection_rate,
                2,
            ),
            "manual_review_rate": round(
                manual_review_rate,
                2,
            ),
        },

        "risk": {
            "average_score": round(
                average_risk_score,
                2,
            ),
            "low": low,
            "medium": medium,
            "high": high,
            "critical": critical,
            "high_risk_total": high + critical,
        },

        "financial": {
            "total_value": round(
                total_value,
                2,
            ),
            "approved_value": round(
                approved_value,
                2,
            ),
            "rejected_value": round(
                rejected_value,
                2,
            ),
            "average_order_value": round(
                average_order_value,
                2,
            ),
        },

        "reviews": {
            "total": len(risk_logs),
            "pending": manual_review,
            "approved": approved,
            "rejected": rejected,
        },
    }