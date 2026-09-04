from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db

from app.models.order import Order

from app.services.analytics_service import AnalyticsService


# =========================================================
# ANALYTICS ROUTER
# =========================================================

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


# =========================================================
# OVERVIEW
# =========================================================

@router.get("/overview")
def get_analytics_overview(
    db: Session = Depends(get_db),
) -> Any:

    try:

        return AnalyticsService.get_dashboard_summary(db)

    except Exception as e:

        print(
            "[ANALYTICS ERROR] Overview:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to fetch analytics overview",
                "error": str(e),
            },
        )


# =========================================================
# ORDER ANALYTICS
# =========================================================

@router.get("/orders")
def get_order_analytics(
    db: Session = Depends(get_db),
) -> Any:

    try:

        return AnalyticsService.get_order_status_distribution(
            db
        )

    except Exception as e:

        print(
            "[ANALYTICS ERROR] Orders:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to fetch order analytics",
                "error": str(e),
            },
        )


# =========================================================
# RISK ANALYTICS
# =========================================================

@router.get("/risk")
def get_risk_analytics(
    db: Session = Depends(get_db),
) -> Any:

    try:

        summary = (
            AnalyticsService.get_dashboard_summary(
                db
            )
        )

        distribution = (
            AnalyticsService.get_risk_distribution(
                db
            )
        )

        risk_data = summary.get(
            "risk",
            {},
        )

        return {
            "average_risk_score": risk_data.get(
                "average_score",
                0,
            ),
            "distribution": distribution,
        }

    except Exception as e:

        print(
            "[ANALYTICS ERROR] Risk:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to fetch risk analytics",
                "error": str(e),
            },
        )


# =========================================================
# MANUAL REVIEW ANALYTICS
# =========================================================

@router.get("/manual-reviews")
def get_manual_review_analytics(
    db: Session = Depends(get_db),
) -> Any:

    try:

        return AnalyticsService.get_manual_review_analytics(
            db
        )

    except Exception as e:

        print(
            "[ANALYTICS ERROR] Manual reviews:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Unable to fetch manual review analytics"
                ),
                "error": str(e),
            },
        )


# =========================================================
# PAYMENT ANALYTICS
# =========================================================

@router.get("/payments")
def get_payment_analytics(
    db: Session = Depends(get_db),
) -> Any:

    try:

        summary = (
            AnalyticsService.get_dashboard_summary(
                db
            )
        )

        payments = summary.get(
            "payments",
            {},
        )

        revenue = summary.get(
            "revenue",
            {},
        )

        return {
            "paid": payments.get(
                "paid",
                0,
            ),
            "failed": payments.get(
                "failed",
                0,
            ),
            "total_revenue": revenue.get(
                "total",
                0,
            ),
        }

    except Exception as e:

        print(
            "[ANALYTICS ERROR] Payments:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to fetch payment analytics",
                "error": str(e),
            },
        )


# =========================================================
# DISCOUNT ANALYTICS
# =========================================================

@router.get("/discounts")
def get_discount_analytics(
    db: Session = Depends(get_db),
) -> Any:

    try:

        # -----------------------------------------------------
        # TOTAL DISCOUNT
        # -----------------------------------------------------

        total_discount = (
            db.query(
                func.coalesce(
                    func.sum(
                        Order.discount_amount
                    ),
                    0,
                )
            )
            .scalar()
            or 0
        )

        # -----------------------------------------------------
        # AVERAGE DISCOUNT
        # -----------------------------------------------------

        average_discount = (
            db.query(
                func.avg(
                    Order.discount_percent
                )
            )
            .filter(
                Order.discount_percent.isnot(None)
            )
            .scalar()
        )

        result = {
            "total_discount_amount": round(
                float(total_discount),
                2,
            ),
            "average_discount_percent": round(
                float(
                    average_discount or 0
                ),
                2,
            ),
        }

        # =====================================================
        # REQUESTED DISCOUNT
        # =====================================================

        if hasattr(
            Order,
            "requested_discount_percent",
        ):

            requested_discount = (
                db.query(
                    func.avg(
                        Order.requested_discount_percent
                    )
                )
                .filter(
                    Order.requested_discount_percent.isnot(
                        None
                    )
                )
                .scalar()
            )

            result[
                "average_requested_discount_percent"
            ] = round(
                float(
                    requested_discount or 0
                ),
                2,
            )

        else:

            result[
                "average_requested_discount_percent"
            ] = 0.0

        # =====================================================
        # APPROVED DISCOUNT
        # =====================================================

        if hasattr(
            Order,
            "approved_discount_percent",
        ):

            approved_discount = (
                db.query(
                    func.avg(
                        Order.approved_discount_percent
                    )
                )
                .filter(
                    Order.approved_discount_percent.isnot(
                        None
                    )
                )
                .scalar()
            )

            result[
                "average_approved_discount_percent"
            ] = round(
                float(
                    approved_discount or 0
                ),
                2,
            )

        else:

            result[
                "average_approved_discount_percent"
            ] = 0.0

        # =====================================================
        # DISCOUNT ADJUSTMENT
        # =====================================================

        if hasattr(
            Order,
            "discount_adjusted",
        ):

            adjusted_orders = (
                db.query(
                    func.count(
                        Order.id
                    )
                )
                .filter(
                    Order.discount_adjusted.is_(True)
                )
                .scalar()
                or 0
            )

            result[
                "adjusted_orders"
            ] = int(
                adjusted_orders
            )

        else:

            result[
                "adjusted_orders"
            ] = 0

        return result

    except Exception as e:

        print(
            "[ANALYTICS ERROR] Discounts:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to fetch discount analytics",
                "error": str(e),
            },
        )


# =========================================================
# INVENTORY ANALYTICS
# =========================================================

@router.get("/inventory")
def get_inventory_analytics(
    db: Session = Depends(get_db),
) -> Any:

    try:

        # -----------------------------------------------------
        # TOTAL ORDERS
        # -----------------------------------------------------

        total_orders = (
            db.query(
                func.count(
                    Order.id
                )
            )
            .scalar()
            or 0
        )

        # =====================================================
        # INVENTORY DEDUCTED
        # =====================================================

        if hasattr(
            Order,
            "inventory_deducted",
        ):

            inventory_deducted = (
                db.query(
                    func.count(
                        Order.id
                    )
                )
                .filter(
                    Order.inventory_deducted.is_(True)
                )
                .scalar()
                or 0
            )

            inventory_pending = (
                db.query(
                    func.count(
                        Order.id
                    )
                )
                .filter(
                    Order.inventory_deducted.is_(False)
                )
                .scalar()
                or 0
            )

        else:

            inventory_deducted = 0

            inventory_pending = int(
                total_orders
            )

        return {
            "total_orders": int(
                total_orders
            ),
            "inventory_deducted": int(
                inventory_deducted
            ),
            "inventory_pending": int(
                inventory_pending
            ),
        }

    except Exception as e:

        print(
            "[ANALYTICS ERROR] Inventory:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to fetch inventory analytics",
                "error": str(e),
            },
        )


# =========================================================
# DAILY ANALYTICS
# =========================================================

@router.get("/daily")
def get_daily_analytics(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
    ),
    db: Session = Depends(get_db),
) -> Any:

    try:

        order_trend = (
            AnalyticsService.get_order_trend(
                db,
                days=days,
            )
        )

        revenue_trend = (
            AnalyticsService.get_revenue_trend(
                db,
                days=days,
            )
        )

        return {
            "days": days,
            "orders": order_trend.get(
                "data",
                [],
            ),
            "revenue": revenue_trend.get(
                "data",
                [],
            ),
        }

    except Exception as e:

        print(
            "[ANALYTICS ERROR] Daily:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to fetch daily analytics",
                "error": str(e),
            },
        )


# =========================================================
# ORDER TREND
# =========================================================

@router.get("/order-trend")
def get_order_trend(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
    ),
    db: Session = Depends(get_db),
) -> Any:

    try:

        return AnalyticsService.get_order_trend(
            db,
            days=days,
        )

    except Exception as e:

        print(
            "[ANALYTICS ERROR] Order trend:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to fetch order trend",
                "error": str(e),
            },
        )


# =========================================================
# REVENUE TREND
# =========================================================

@router.get("/revenue-trend")
def get_revenue_trend(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
    ),
    db: Session = Depends(get_db),
) -> Any:

    try:

        return AnalyticsService.get_revenue_trend(
            db,
            days=days,
        )

    except Exception as e:

        print(
            "[ANALYTICS ERROR] Revenue trend:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to fetch revenue trend",
                "error": str(e),
            },
        )


# =========================================================
# MERCHANT PERFORMANCE
# =========================================================

@router.get("/merchants")
def get_merchant_performance(
    db: Session = Depends(get_db),
) -> Any:

    try:

        return AnalyticsService.get_merchant_performance(
            db
        )

    except Exception as e:

        print(
            "[ANALYTICS ERROR] Merchant performance:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to fetch merchant analytics",
                "error": str(e),
            },
        )


# =========================================================
# RECENT ACTIVITY
# =========================================================

@router.get("/recent-activity")
def get_recent_activity(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
) -> Any:

    try:

        return AnalyticsService.get_recent_activity(
            db,
            limit=limit,
        )

    except Exception as e:

        print(
            "[ANALYTICS ERROR] Recent activity:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to fetch recent activity",
                "error": str(e),
            },
        )


# =========================================================
# DASHBOARD
# =========================================================

@router.get("/dashboard")
def get_dashboard_analytics(
    days: int = Query(
        default=30,
        ge=1,
        le=365,
    ),
    db: Session = Depends(get_db),
) -> Any:

    try:

        print()
        print("=" * 70)
        print("PAYPILOT ANALYTICS DASHBOARD")
        print("=" * 70)

        # =====================================================
        # SUMMARY
        # =====================================================

        summary = (
            AnalyticsService.get_dashboard_summary(
                db
            )
        )

        # =====================================================
        # RISK
        # =====================================================

        risk = (
            AnalyticsService.get_risk_distribution(
                db
            )
        )

        # =====================================================
        # ORDER STATUS
        # =====================================================

        status = (
            AnalyticsService.get_order_status_distribution(
                db
            )
        )

        # =====================================================
        # ORDER TREND
        # =====================================================

        order_trend = (
            AnalyticsService.get_order_trend(
                db,
                days=days,
            )
        )

        # =====================================================
        # REVENUE TREND
        # =====================================================

        revenue_trend = (
            AnalyticsService.get_revenue_trend(
                db,
                days=days,
            )
        )

        # =====================================================
        # MERCHANT PERFORMANCE
        # =====================================================

        merchant_performance = (
            AnalyticsService.get_merchant_performance(
                db
            )
        )

        # =====================================================
        # MANUAL REVIEWS
        # =====================================================

        manual_reviews = (
            AnalyticsService.get_manual_review_analytics(
                db
            )
        )

        # =====================================================
        # RECENT ACTIVITY
        # =====================================================

        recent_activity = (
            AnalyticsService.get_recent_activity(
                db,
                limit=20,
            )
        )

        print(
            "Analytics dashboard generated successfully."
        )

        print("=" * 70)

        # =====================================================
        # RESPONSE
        # =====================================================

        return {
            "summary": summary,

            "risk": risk,

            "order_status": status,

            "order_trend": order_trend,

            "revenue_trend": revenue_trend,

            "merchant_performance": (
                merchant_performance
            ),

            "manual_reviews": (
                manual_reviews
            ),

            "recent_activity": (
                recent_activity
            ),

        }

    except Exception as e:

        print()
        print("=" * 70)
        print("PAYPILOT ANALYTICS DASHBOARD ERROR")
        print("=" * 70)

        print(
            f"Error type: {type(e).__name__}"
        )

        print(
            f"Error: {e}"
        )

        print("=" * 70)

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Unable to fetch dashboard analytics"
                ),
                "error": str(e),
            },
        )