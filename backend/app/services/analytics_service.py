from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.payment import Payment
from app.models.manual_review import ManualReview
from app.models.merchant import Merchant
from app.models.audit_log import AuditLog


# =========================================================
# ANALYTICS SERVICE
# =========================================================
#
# Read-only analytics layer.
#
# IMPORTANT:
# This service DOES NOT:
#
#   - create orders
#   - modify orders
#   - process payments
#   - modify inventory
#   - create manual reviews
#   - modify audit logs
#
# It only reads existing database information.
#
# =========================================================


class AnalyticsService:

    # =====================================================
    # ORDER STATUS GROUPS
    # =====================================================

    APPROVED_ORDER_STATUSES = (
        "APPROVED",
        "PAID",
        "DISCOUNT_ADJUSTED",
    )

    REJECTED_ORDER_STATUSES = (
        "REJECTED",
    )

    BLOCKED_ORDER_STATUSES = (
        "BLOCKED",
    )

    MANUAL_REVIEW_ORDER_STATUSES = (
        "MANUAL_REVIEW_REQUIRED",
    )

    # =====================================================
    # PAYMENT STATUSES
    # =====================================================

    PAYMENT_SUCCESS_STATUSES = (
        "CAPTURED",
        "PAID",
        "SUCCESS",
    )

    PAYMENT_FAILED_STATUSES = (
        "FAILED",
        "FAILURE",
    )

    # =====================================================
    # HELPER
    # =====================================================

    @staticmethod
    def _upper(value):
        """
        Safely convert a database enum/string value
        to uppercase.
        """

        if value is None:
            return ""

        return str(value).upper()

    # =====================================================
    # DASHBOARD SUMMARY
    # =====================================================

    @staticmethod
    def get_dashboard_summary(db: Session):

        # -------------------------------------------------
        # TOTAL ORDERS
        # -------------------------------------------------

        total_orders = (
            db.query(func.count(Order.id))
            .scalar()
            or 0
        )

        # -------------------------------------------------
        # APPROVED ORDERS
        # -------------------------------------------------

        approved_orders = (
            db.query(func.count(Order.id))
            .filter(
                func.upper(Order.status).in_(
                    AnalyticsService.APPROVED_ORDER_STATUSES
                )
            )
            .scalar()
            or 0
        )

        # -------------------------------------------------
        # REJECTED
        # -------------------------------------------------

        rejected_orders = (
            db.query(func.count(Order.id))
            .filter(
                func.upper(Order.status).in_(
                    AnalyticsService.REJECTED_ORDER_STATUSES
                )
            )
            .scalar()
            or 0
        )

        # -------------------------------------------------
        # BLOCKED
        # -------------------------------------------------

        blocked_orders = (
            db.query(func.count(Order.id))
            .filter(
                func.upper(Order.status).in_(
                    AnalyticsService.BLOCKED_ORDER_STATUSES
                )
            )
            .scalar()
            or 0
        )

        # -------------------------------------------------
        # MANUAL REVIEW
        # -------------------------------------------------

        manual_review_orders = (
            db.query(func.count(Order.id))
            .filter(
                func.upper(Order.status).in_(
                    AnalyticsService.MANUAL_REVIEW_ORDER_STATUSES
                )
            )
            .scalar()
            or 0
        )

        # -------------------------------------------------
        # PAID ORDERS
        # -------------------------------------------------

        paid_order_status_count = (
            db.query(func.count(Order.id))
            .filter(
                func.upper(Order.status) == "PAID"
            )
            .scalar()
            or 0
        )

        # -------------------------------------------------
        # DISCOUNT ADJUSTED ORDERS
        # -------------------------------------------------

        discount_adjusted_orders = (
            db.query(func.count(Order.id))
            .filter(
                func.upper(Order.status)
                == "DISCOUNT_ADJUSTED"
            )
            .scalar()
            or 0
        )

        # -------------------------------------------------
        # OTHER ORDERS
        # -------------------------------------------------

        known_status_count = (
            int(approved_orders)
            + int(rejected_orders)
            + int(blocked_orders)
            + int(manual_review_orders)
        )

        other_orders = max(
            int(total_orders) - known_status_count,
            0,
        )

        # -------------------------------------------------
        # PAYMENT COUNTS
        # -------------------------------------------------

        paid_payments = (
            db.query(func.count(Payment.id))
            .filter(
                func.upper(Payment.status).in_(
                    AnalyticsService.PAYMENT_SUCCESS_STATUSES
                )
            )
            .scalar()
            or 0
        )

        failed_payments = (
            db.query(func.count(Payment.id))
            .filter(
                func.upper(Payment.status).in_(
                    AnalyticsService.PAYMENT_FAILED_STATUSES
                )
            )
            .scalar()
            or 0
        )

        total_payment_attempts = (
            db.query(func.count(Payment.id))
            .scalar()
            or 0
        )

        # -------------------------------------------------
        # PAYMENT SUCCESS RATE
        # -------------------------------------------------

        payment_success_rate = 0.0

        if total_payment_attempts > 0:
            payment_success_rate = (
                float(paid_payments)
                / float(total_payment_attempts)
            ) * 100

        # -------------------------------------------------
        # PAYMENT REVENUE
        # -------------------------------------------------

        total_revenue = (
            db.query(
                func.coalesce(
                    func.sum(Payment.amount),
                    0,
                )
            )
            .filter(
                func.upper(Payment.status).in_(
                    AnalyticsService.PAYMENT_SUCCESS_STATUSES
                )
            )
            .scalar()
            or 0
        )

        # -------------------------------------------------
        # APPROVED ORDER VALUE
        # -------------------------------------------------

        approved_order_value = (
            db.query(
                func.coalesce(
                    func.sum(Order.final_amount),
                    0,
                )
            )
            .filter(
                func.upper(Order.status).in_(
                    AnalyticsService.APPROVED_ORDER_STATUSES
                )
            )
            .scalar()
            or 0
        )

        # -------------------------------------------------
        # AVERAGE ORDER VALUE
        # -------------------------------------------------

        average_order_value = 0.0

        if approved_orders > 0:
            average_order_value = (
                float(approved_order_value)
                / float(approved_orders)
            )

        # -------------------------------------------------
        # RISK
        # -------------------------------------------------

        average_risk_score = (
            db.query(
                func.avg(Order.risk_score)
            )
            .filter(
                Order.risk_score.isnot(None)
            )
            .scalar()
        )

        if average_risk_score is None:
            average_risk_score = 0.0

        # -------------------------------------------------
        # HIGH + CRITICAL RISK
        # -------------------------------------------------

        high_risk_orders = (
            db.query(func.count(Order.id))
            .filter(
                func.upper(Order.risk_level).in_(
                    [
                        "HIGH",
                        "CRITICAL",
                    ]
                )
            )
            .scalar()
            or 0
        )

        # -------------------------------------------------
        # MANUAL REVIEWS
        # -------------------------------------------------

        total_reviews = (
            db.query(func.count(ManualReview.id))
            .scalar()
            or 0
        )

        pending_reviews = (
            db.query(func.count(ManualReview.id))
            .filter(
                func.upper(ManualReview.status)
                == "PENDING"
            )
            .scalar()
            or 0
        )

        approved_reviews = (
            db.query(func.count(ManualReview.id))
            .filter(
                func.upper(ManualReview.status)
                == "APPROVED"
            )
            .scalar()
            or 0
        )

        rejected_reviews = (
            db.query(func.count(ManualReview.id))
            .filter(
                func.upper(ManualReview.status)
                == "REJECTED"
            )
            .scalar()
            or 0
        )

        completed_reviews = (
            int(approved_reviews)
            + int(rejected_reviews)
        )

        review_approval_rate = 0.0

        if completed_reviews > 0:
            review_approval_rate = (
                float(approved_reviews)
                / float(completed_reviews)
            ) * 100

        # -------------------------------------------------
        # MERCHANTS
        # -------------------------------------------------

        total_merchants = (
            db.query(func.count(Merchant.id))
            .scalar()
            or 0
        )

        active_merchants = (
            db.query(func.count(Merchant.id))
            .filter(
                Merchant.is_active.is_(True)
            )
            .scalar()
            or 0
        )

        # -------------------------------------------------
        # DISCOUNTS
        # -------------------------------------------------

        average_discount = (
            db.query(
                func.avg(Order.discount_percent)
            )
            .filter(
                Order.discount_percent.isnot(None)
            )
            .scalar()
        )

        if average_discount is None:
            average_discount = 0.0

        adjusted_discount_orders = (
            db.query(func.count(Order.id))
            .filter(
                Order.discount_adjusted.is_(True)
            )
            .scalar()
            or 0
        )

        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return {
            "orders": {
                "total": int(total_orders),
                "approved": int(approved_orders),
                "rejected": int(rejected_orders),
                "blocked": int(blocked_orders),
                "manual_review": int(manual_review_orders),
                "paid": int(paid_order_status_count),
                "discount_adjusted": int(
                    discount_adjusted_orders
                ),
                "other": int(other_orders),
            },

            "payments": {
                "total_attempts": int(
                    total_payment_attempts
                ),
                "paid": int(paid_payments),
                "failed": int(failed_payments),
                "success_rate": round(
                    float(payment_success_rate),
                    2,
                ),
            },

            "revenue": {
                "total": round(
                    float(total_revenue),
                    2,
                ),
                "approved_order_value": round(
                    float(approved_order_value),
                    2,
                ),
                "average_order_value": round(
                    float(average_order_value),
                    2,
                ),
            },

            "risk": {
                "average_score": round(
                    float(average_risk_score),
                    2,
                ),
                "high_and_critical": int(
                    high_risk_orders
                ),
            },

            "manual_reviews": {
                "total": int(total_reviews),
                "pending": int(pending_reviews),
                "approved": int(approved_reviews),
                "rejected": int(rejected_reviews),
                "approval_rate": round(
                    float(review_approval_rate),
                    2,
                ),
            },

            "discounts": {
                "average_percent": round(
                    float(average_discount),
                    2,
                ),
                "adjusted_orders": int(
                    adjusted_discount_orders
                ),
            },

            "merchants": {
                "total": int(total_merchants),
                "active": int(active_merchants),
            },
        }

    # =====================================================
    # RISK DISTRIBUTION
    # =====================================================

    @staticmethod
    def get_risk_distribution(db: Session):

        levels = [
            "LOW",
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        ]

        counts = {}

        for level in levels:

            count = (
                db.query(func.count(Order.id))
                .filter(
                    func.upper(Order.risk_level)
                    == level
                )
                .scalar()
                or 0
            )

            counts[level.lower()] = int(count)

        total = sum(counts.values())

        percentages = {}

        for level, count in counts.items():

            if total > 0:
                percentages[level] = round(
                    (
                        float(count)
                        / float(total)
                    ) * 100,
                    2,
                )
            else:
                percentages[level] = 0.0

        return {
            "total_risk_evaluated_orders": int(total),
            "counts": counts,
            "percentages": percentages,
        }

    # =====================================================
    # ORDER STATUS DISTRIBUTION
    # =====================================================

    @staticmethod
    def get_order_status_distribution(
        db: Session,
    ):

        rows = (
            db.query(
                Order.status,
                func.count(Order.id),
            )
            .group_by(Order.status)
            .all()
        )

        result = {}

        for status, count in rows:

            if status is None:
                status = "UNKNOWN"

            normalized_status = str(status).upper()

            result[normalized_status] = int(count)

        expected_statuses = [
            "APPROVED",
            "PAID",
            "REJECTED",
            "BLOCKED",
            "MANUAL_REVIEW_REQUIRED",
            "DISCOUNT_ADJUSTED",
        ]

        for status in expected_statuses:

            if status not in result:
                result[status] = 0

        return {
            "total_orders": int(
                sum(result.values())
            ),
            "statuses": result,
        }

    # =====================================================
    # ORDER TREND
    # =====================================================

    @staticmethod
    def get_order_trend(
        db: Session,
        days: int = 30,
    ):

        days = max(
            1,
            min(days, 365),
        )

        start_date = (
            datetime.utcnow()
            - timedelta(days=days - 1)
        ).date()

        start_datetime = datetime.combine(
            start_date,
            datetime.min.time(),
        )

        orders = (
            db.query(Order)
            .filter(
                Order.created_at
                >= start_datetime
            )
            .order_by(
                Order.created_at.asc()
            )
            .all()
        )

        daily = {}

        for order in orders:

            if not order.created_at:
                continue

            date_key = (
                order.created_at
                .date()
                .isoformat()
            )

            if date_key not in daily:
                daily[date_key] = {
                    "date": date_key,
                    "orders": 0,
                    "approved": 0,
                    "paid": 0,
                    "discount_adjusted": 0,
                    "rejected": 0,
                    "blocked": 0,
                    "manual_review": 0,
                    "revenue": 0.0,
                }

            daily[date_key]["orders"] += 1

            status = AnalyticsService._upper(
                order.status
            )

            if status == "APPROVED":

                daily[date_key]["approved"] += 1

                daily[date_key]["revenue"] += float(
                    order.final_amount or 0
                )

            elif status == "PAID":

                daily[date_key]["paid"] += 1
                daily[date_key]["approved"] += 1

                daily[date_key]["revenue"] += float(
                    order.final_amount or 0
                )

            elif status == "DISCOUNT_ADJUSTED":

                daily[date_key][
                    "discount_adjusted"
                ] += 1

                daily[date_key]["approved"] += 1

                daily[date_key]["revenue"] += float(
                    order.final_amount or 0
                )

            elif status == "REJECTED":

                daily[date_key]["rejected"] += 1

            elif status == "BLOCKED":

                daily[date_key]["blocked"] += 1

            elif status == "MANUAL_REVIEW_REQUIRED":

                daily[date_key][
                    "manual_review"
                ] += 1

        # -------------------------------------------------
        # INCLUDE EMPTY DAYS
        # -------------------------------------------------

        result = []

        for i in range(days):

            current_date = (
                start_date
                + timedelta(days=i)
            )

            key = current_date.isoformat()

            item = daily.get(
                key,
                {
                    "date": key,
                    "orders": 0,
                    "approved": 0,
                    "paid": 0,
                    "discount_adjusted": 0,
                    "rejected": 0,
                    "blocked": 0,
                    "manual_review": 0,
                    "revenue": 0.0,
                },
            )

            item["revenue"] = round(
                float(item["revenue"]),
                2,
            )

            result.append(item)

        return {
            "days": days,
            "data": result,
        }

    # =====================================================
    # REVENUE TREND
    # =====================================================

    @staticmethod
    def get_revenue_trend(
        db: Session,
        days: int = 30,
    ):

        days = max(
            1,
            min(days, 365),
        )

        start_date = (
            datetime.utcnow()
            - timedelta(days=days - 1)
        ).date()

        start_datetime = datetime.combine(
            start_date,
            datetime.min.time(),
        )

        orders = (
            db.query(Order)
            .filter(
                Order.created_at
                >= start_datetime
            )
            .filter(
                func.upper(Order.status).in_(
                    AnalyticsService.APPROVED_ORDER_STATUSES
                )
            )
            .order_by(
                Order.created_at.asc()
            )
            .all()
        )

        daily = {}

        for order in orders:

            if not order.created_at:
                continue

            date_key = (
                order.created_at
                .date()
                .isoformat()
            )

            if date_key not in daily:
                daily[date_key] = {
                    "date": date_key,
                    "revenue": 0.0,
                    "orders": 0,
                    "average_order_value": 0.0,
                }

            daily[date_key]["revenue"] += float(
                order.final_amount or 0
            )

            daily[date_key]["orders"] += 1

        result = []

        for i in range(days):

            current_date = (
                start_date
                + timedelta(days=i)
            )

            key = current_date.isoformat()

            item = daily.get(
                key,
                {
                    "date": key,
                    "revenue": 0.0,
                    "orders": 0,
                    "average_order_value": 0.0,
                },
            )

            if item["orders"] > 0:

                item["average_order_value"] = (
                    float(item["revenue"])
                    / float(item["orders"])
                )

            item["revenue"] = round(
                float(item["revenue"]),
                2,
            )

            item["average_order_value"] = round(
                float(
                    item["average_order_value"]
                ),
                2,
            )

            result.append(item)

        return {
            "days": days,
            "data": result,
        }

    # =====================================================
    # MERCHANT PERFORMANCE
    # =====================================================

    @staticmethod
    def get_merchant_performance(
        db: Session,
    ):

        merchants = (
            db.query(Merchant)
            .order_by(Merchant.id.asc())
            .all()
        )

        result = []

        for merchant in merchants:

            # -------------------------------------------------
            # TOTAL ORDERS
            # -------------------------------------------------

            total_orders = (
                db.query(func.count(Order.id))
                .filter(
                    Order.merchant_id
                    == merchant.id
                )
                .scalar()
                or 0
            )

            # -------------------------------------------------
            # SUCCESSFUL ORDERS
            # -------------------------------------------------

            approved_orders = (
                db.query(func.count(Order.id))
                .filter(
                    Order.merchant_id
                    == merchant.id
                )
                .filter(
                    func.upper(Order.status).in_(
                        AnalyticsService.APPROVED_ORDER_STATUSES
                    )
                )
                .scalar()
                or 0
            )

            # -------------------------------------------------
            # REJECTED ORDERS
            # -------------------------------------------------

            rejected_orders = (
                db.query(func.count(Order.id))
                .filter(
                    Order.merchant_id
                    == merchant.id
                )
                .filter(
                    func.upper(Order.status).in_(
                        AnalyticsService.REJECTED_ORDER_STATUSES
                    )
                )
                .scalar()
                or 0
            )

            # -------------------------------------------------
            # REVENUE
            # -------------------------------------------------

            revenue = (
                db.query(
                    func.coalesce(
                        func.sum(Order.final_amount),
                        0,
                    )
                )
                .filter(
                    Order.merchant_id
                    == merchant.id
                )
                .filter(
                    func.upper(Order.status).in_(
                        AnalyticsService.APPROVED_ORDER_STATUSES
                    )
                )
                .scalar()
                or 0
            )

            # -------------------------------------------------
            # AVERAGE RISK
            # -------------------------------------------------

            average_risk = (
                db.query(
                    func.avg(Order.risk_score)
                )
                .filter(
                    Order.merchant_id
                    == merchant.id
                )
                .filter(
                    Order.risk_score.isnot(None)
                )
                .scalar()
            )

            if average_risk is None:
                average_risk = 0.0

            # -------------------------------------------------
            # APPROVAL RATE
            # -------------------------------------------------

            approval_rate = 0.0

            if total_orders > 0:

                approval_rate = (
                    float(approved_orders)
                    / float(total_orders)
                ) * 100

            result.append(
                {
                    "merchant_id": merchant.id,
                    "merchant_name": merchant.name,
                    "active": bool(
                        merchant.is_active
                    ),
                    "orders": int(
                        total_orders
                    ),
                    "approved_orders": int(
                        approved_orders
                    ),
                    "rejected_orders": int(
                        rejected_orders
                    ),
                    "approval_rate": round(
                        float(approval_rate),
                        2,
                    ),
                    "revenue": round(
                        float(revenue),
                        2,
                    ),
                    "average_risk_score": round(
                        float(average_risk),
                        2,
                    ),
                }
            )

        result.sort(
            key=lambda item: item["revenue"],
            reverse=True,
        )

        return result

    # =====================================================
    # MANUAL REVIEW ANALYTICS
    # =====================================================

    @staticmethod
    def get_manual_review_analytics(
        db: Session,
    ):

        total = (
            db.query(func.count(ManualReview.id))
            .scalar()
            or 0
        )

        pending = (
            db.query(func.count(ManualReview.id))
            .filter(
                func.upper(ManualReview.status)
                == "PENDING"
            )
            .scalar()
            or 0
        )

        approved = (
            db.query(func.count(ManualReview.id))
            .filter(
                func.upper(ManualReview.status)
                == "APPROVED"
            )
            .scalar()
            or 0
        )

        rejected = (
            db.query(func.count(ManualReview.id))
            .filter(
                func.upper(ManualReview.status)
                == "REJECTED"
            )
            .scalar()
            or 0
        )

        completed = (
            int(approved)
            + int(rejected)
        )

        approval_rate = 0.0
        rejection_rate = 0.0

        if completed > 0:

            approval_rate = (
                float(approved)
                / float(completed)
            ) * 100

            rejection_rate = (
                float(rejected)
                / float(completed)
            ) * 100

        return {
            "total": int(total),
            "pending": int(pending),
            "approved": int(approved),
            "rejected": int(rejected),
            "completed": int(completed),
            "approval_rate": round(
                approval_rate,
                2,
            ),
            "rejection_rate": round(
                rejection_rate,
                2,
            ),
        }

    # =====================================================
    # RECENT AUDIT ACTIVITY
    # =====================================================
    #
    # IMPORTANT:
    #
    # The database may contain duplicate audit records.
    #
    # We DO NOT delete those records here.
    #
    # Instead, the analytics/dashboard layer removes
    # duplicate-looking events from the response.
    #
    # This prevents the dashboard from showing the same
    # audit activity 5 times.
    #
    # =====================================================

    @staticmethod
    def get_recent_activity(
        db: Session,
        limit: int = 20,
    ):

        limit = max(
            1,
            min(limit, 100),
        )

        # -------------------------------------------------
        # Fetch more records than requested.
        #
        # Why?
        #
        # If the newest 20 rows contain duplicates,
        # we still want to return up to `limit`
        # UNIQUE activities.
        # -------------------------------------------------

        fetch_limit = min(
            max(limit * 5, 50),
            500,
        )

        logs = (
            db.query(AuditLog)
            .order_by(
                AuditLog.created_at.desc(),
                AuditLog.id.desc(),
            )
            .limit(fetch_limit)
            .all()
        )

        result = []

        # -------------------------------------------------
        # Used to identify duplicate audit events.
        #
        # IMPORTANT:
        #
        # We intentionally do NOT use only message.
        #
        # The same message can legitimately occur for
        # different orders/events.
        # -------------------------------------------------

        seen = set()

        for log in logs:

            # -------------------------------------------------
            # Build duplicate signature
            # -------------------------------------------------

            signature = (
                log.order_id,
                log.merchant_id,
                log.event_type,
                log.message,
                log.old_status,
                log.new_status,
                (
                    float(log.risk_score)
                    if log.risk_score is not None
                    else None
                ),
                log.risk_level,
                log.performed_by,
            )

            # -------------------------------------------------
            # Skip duplicate-looking events
            # -------------------------------------------------

            if signature in seen:
                continue

            seen.add(signature)

            result.append(
                {
                    "id": log.id,

                    "order_id": log.order_id,

                    "merchant_id": log.merchant_id,

                    "event_type": log.event_type,

                    "message": log.message,

                    "old_status": log.old_status,

                    "new_status": log.new_status,

                    "risk_score": (
                        float(log.risk_score)
                        if log.risk_score is not None
                        else None
                    ),

                    "risk_level": log.risk_level,

                    "performed_by": log.performed_by,

                    "created_at": (
                        log.created_at.isoformat()
                        if log.created_at
                        else None
                    ),
                }
            )

            # -------------------------------------------------
            # Stop after collecting requested unique records
            # -------------------------------------------------

            if len(result) >= limit:
                break

        return result