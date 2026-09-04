import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.database import get_db

from app.models.merchant import Merchant

from app.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
)

from app.schemas.order import OrderCreate

from app.services.agent_service import AgentService

from app.services.recommendation_service import (
    RecommendationService,
)

from app.routes.order import (
    create_order_internal,
)


# =========================================================
# SAFE VALUE HELPERS
# =========================================================

def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    if value is None:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(
    value: Any,
    default: int = 0,
) -> int:
    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# =========================================================
# NORMALIZE ORDER RESULT
# =========================================================
#
# create_order_internal() may return:
#   1. SQLAlchemy Order object
#   2. Starlette JSONResponse
#   3. dict
#
# /agent/chat must support all three because the order route
# is also used directly by the normal HTTP API.
# =========================================================

def normalize_order_result(
    result: Any,
) -> dict:
    if result is None:
        raise RuntimeError(
            "Order creation returned no result."
        )

    # -----------------------------------------------------
    # DICT
    # -----------------------------------------------------

    if isinstance(result, dict):
        return result

    # -----------------------------------------------------
    # JSONResponse
    # -----------------------------------------------------

    if isinstance(result, JSONResponse):
        try:
            raw_body = result.body

            if isinstance(raw_body, bytes):
                raw_body = raw_body.decode("utf-8")

            if isinstance(raw_body, str):
                data = json.loads(raw_body)
            elif isinstance(raw_body, dict):
                data = raw_body
            else:
                data = {}

            if not isinstance(data, dict):
                raise RuntimeError(
                    "Order response JSON is not an object."
                )

            return data

        except Exception as e:
            raise RuntimeError(
                "Unable to decode order JSONResponse: "
                f"{e}"
            )

    # -----------------------------------------------------
    # STARLETTE RESPONSE FALLBACK
    # -----------------------------------------------------

    if hasattr(result, "body"):
        try:
            raw_body = result.body

            if isinstance(raw_body, bytes):
                raw_body = raw_body.decode("utf-8")

            data = json.loads(raw_body)

            if isinstance(data, dict):
                return data

        except Exception:
            pass

    # -----------------------------------------------------
    # SQLALCHEMY ORDER OBJECT
    # -----------------------------------------------------

    if hasattr(result, "id"):
        return {
            "id": getattr(result, "id", None),
            "merchant_id": getattr(
                result,
                "merchant_id",
                None,
            ),
            "product_id": getattr(
                result,
                "product_id",
                None,
            ),
            "quantity": getattr(
                result,
                "quantity",
                None,
            ),
            "original_amount": getattr(
                result,
                "original_amount",
                None,
            ),
            "discount_percent": getattr(
                result,
                "discount_percent",
                None,
            ),
            "discount_amount": getattr(
                result,
                "discount_amount",
                None,
            ),
            "final_amount": getattr(
                result,
                "final_amount",
                None,
            ),
            "status": getattr(
                result,
                "status",
                None,
            ),
            "risk_score": getattr(
                result,
                "risk_score",
                None,
            ),
            "risk_level": getattr(
                result,
                "risk_level",
                None,
            ),
            "risk_reason": getattr(
                result,
                "risk_reason",
                None,
            ),
            "risk_factors": getattr(
                result,
                "risk_factors",
                None,
            ),
            "risk_reasons": getattr(
                result,
                "risk_reasons",
                None,
            ),
            "ai_explanation": getattr(
                result,
                "ai_explanation",
                None,
            ),
        }

    raise RuntimeError(
        "Unsupported order creation result type: "
        f"{type(result).__name__}"
    )


def order_value(
    order_data: dict,
    key: str,
    default: Any = None,
) -> Any:
    return order_data.get(key, default)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/agent",
    tags=["AI Agent"],
)


# =========================================================
# POST /agent/recommendations
# =========================================================
#
# AI GROWTH AGENT
#
# Provides:
#   - Upsell recommendations
#   - Cross-sell recommendations
#
# IMPORTANT:
#
# This endpoint DOES NOT:
#
#   - create an order
#   - create a payment
#   - deduct inventory
#   - apply discounts
#   - authorize money movement
#
# It is recommendation-only.
#
# The user must explicitly choose a recommendation.
#
# After that, the normal /agent/chat flow handles
# the actual order.
#
# =========================================================

@router.post(
    "/recommendations"
)
def get_growth_recommendations(
    request: dict,
    db: Session = Depends(get_db),
):
    """
    Generate bounded AI upsell and cross-sell
    recommendations.
    """

    # =====================================================
    # 1. GET REQUEST VALUES
    # =====================================================

    merchant_id = request.get(
        "merchant_id"
    )

    product_id = request.get(
        "product_id"
    )

    # =====================================================
    # 2. VALIDATE MERCHANT ID
    # =====================================================

    try:
        merchant_id = int(
            merchant_id
        )

    except (
        TypeError,
        ValueError,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "merchant_id must be a valid integer."
            ),
        )

    if merchant_id <= 0:

        raise HTTPException(
            status_code=400,
            detail="Invalid merchant_id.",
        )

    # =====================================================
    # 3. VALIDATE PRODUCT ID
    # =====================================================

    try:
        product_id = int(
            product_id
        )

    except (
        TypeError,
        ValueError,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "product_id must be a valid integer."
            ),
        )

    if product_id <= 0:

        raise HTTPException(
            status_code=400,
            detail="Invalid product_id.",
        )

    # =====================================================
    # 4. VALIDATE MERCHANT
    # =====================================================

    merchant = (
        db.query(Merchant)
        .filter(
            Merchant.id == merchant_id
        )
        .first()
    )

    if not merchant:

        raise HTTPException(
            status_code=404,
            detail="Merchant not found.",
        )

    # =====================================================
    # 5. CHECK MERCHANT ACTIVE STATUS
    # =====================================================

    if hasattr(
        merchant,
        "is_active",
    ):

        if not merchant.is_active:

            raise HTTPException(
                status_code=400,
                detail="Merchant is inactive.",
            )

    elif hasattr(
        merchant,
        "active",
    ):

        if not merchant.active:

            raise HTTPException(
                status_code=400,
                detail="Merchant is inactive.",
            )

    # =====================================================
    # 6. GENERATE RECOMMENDATIONS
    # =====================================================

    try:

        result = (
            RecommendationService.recommend(
                db=db,
                merchant_id=merchant_id,
                product_id=product_id,
            )
        )

    except Exception as e:

        db.rollback()

        print(
            "========================================"
        )

        print(
            "GROWTH RECOMMENDATION ERROR:"
        )

        print(
            repr(e)
        )

        print(
            "========================================"
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Unable to generate AI "
                    "growth recommendations."
                ),
                "error": str(e),
            },
        )

    # =====================================================
    # 7. RECOMMENDATION FAILURE
    # =====================================================

    if not result.get(
        "success",
        False,
    ):

        raise HTTPException(
            status_code=404,
            detail=result.get(
                "message",
                "Unable to generate recommendations.",
            ),
        )

    # =====================================================
    # 8. RETURN RECOMMENDATIONS
    # =====================================================

    return result


# =========================================================
# POST /agent/chat
# =========================================================

@router.post(
    "/chat",
    response_model=AgentChatResponse,
)
async def agent_chat(
    request: AgentChatRequest,
    db: Session = Depends(get_db),
):

    try:

        # =====================================================
        # 1. VALIDATE MERCHANT
        # =====================================================

        merchant = (
            db.query(Merchant)
            .filter(
                Merchant.id == request.merchant_id
            )
            .first()
        )

        if not merchant:

            raise HTTPException(
                status_code=404,
                detail="Merchant not found",
            )

        # =====================================================
        # 2. CHECK MERCHANT ACTIVE STATUS
        # =====================================================

        if hasattr(
            merchant,
            "is_active",
        ):

            if not merchant.is_active:

                raise HTTPException(
                    status_code=400,
                    detail="Merchant is inactive",
                )

        elif hasattr(
            merchant,
            "active",
        ):

            if not merchant.active:

                raise HTTPException(
                    status_code=400,
                    detail="Merchant is inactive",
                )

        # =====================================================
        # 3. VALIDATE MESSAGE
        # =====================================================

        message = str(
            request.message or ""
        ).strip()

        if not message:

            raise HTTPException(
                status_code=400,
                detail="Message cannot be empty",
            )

        # =====================================================
        # 4. DETECT INTENT
        # =====================================================

        intent = AgentService.detect_intent(
            message
        )

        intent = str(
            intent or "GENERAL_QUERY"
        ).upper()

        # =====================================================
        # 5. CATALOG QUERY
        # =====================================================

        if intent == "CATALOG_QUERY":

            result = AgentService.catalog_response(
                db=db,
                merchant_id=request.merchant_id,
            )

            return AgentChatResponse(
                message=result.get(
                    "message",
                    "No products found.",
                ),

                intent="CATALOG_QUERY",

                merchant_id=(
                    request.merchant_id
                ),

                manual_review_required=False,
            )

        # =====================================================
        # 6. GENERAL QUERY
        # =====================================================

        if intent == "GENERAL_QUERY":

            return AgentChatResponse(
                message=(
                    "I can help with PayPilot "
                    "products, inventory, discounts, "
                    "and orders. "
                    "For example: "
                    "'Buy 2 Test Laptops with 10% discount'."
                ),

                intent="GENERAL_QUERY",

                merchant_id=(
                    request.merchant_id
                ),

                manual_review_required=False,
            )

        # =====================================================
        # 7. CREATE ORDER
        # =====================================================

        if intent != "CREATE_ORDER":

            return AgentChatResponse(
                message=(
                    "I could not determine the requested "
                    "PayPilot operation."
                ),

                intent="GENERAL_QUERY",

                merchant_id=(
                    request.merchant_id
                ),

                manual_review_required=False,
            )

        # =====================================================
        # 8. EXTRACT QUANTITY
        # =====================================================

        try:

            quantity = int(
                AgentService.extract_quantity(
                    message
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            quantity = 1

        # Safety fallback

        if quantity <= 0:

            return AgentChatResponse(
                message=(
                    "Please specify a valid quantity "
                    "greater than zero."
                ),

                intent="CREATE_ORDER",

                merchant_id=(
                    request.merchant_id
                ),

                quantity=quantity,

                manual_review_required=False,
            )

        # =====================================================
        # 9. EXTRACT DISCOUNT
        # =====================================================

        try:

            discount = float(
                AgentService.extract_discount(
                    message
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            discount = 0.0

        if discount < 0:

            return AgentChatResponse(
                message=(
                    "Discount cannot be negative."
                ),

                intent="CREATE_ORDER",

                merchant_id=(
                    request.merchant_id
                ),

                quantity=quantity,

                requested_discount_percent=(
                    discount
                ),

                manual_review_required=False,
            )

        # =====================================================
        # 10. DISCOUNT UPPER BOUND
        # =====================================================

        if discount > 100:

            return AgentChatResponse(
                message=(
                    "Discount cannot be greater than 100%."
                ),

                intent="CREATE_ORDER",

                merchant_id=(
                    request.merchant_id
                ),

                quantity=quantity,

                requested_discount_percent=(
                    discount
                ),

                manual_review_required=False,
            )

        # =====================================================
        # 11. FIND PRODUCT
        # =====================================================

        product = AgentService.find_product(
            db=db,
            merchant_id=request.merchant_id,
            message=message,
        )

        # =====================================================
        # 12. PRODUCT NOT FOUND
        # =====================================================

        if not product:

            return AgentChatResponse(
                message=(
                    "I could not identify a product "
                    "from your request.\n\n"
                    "Please provide the product name "
                    "or SKU.\n\n"
                    "Example:\n"
                    "'I want 1 Mechanical Keyboard'"
                ),

                intent="CREATE_ORDER",

                merchant_id=(
                    request.merchant_id
                ),

                quantity=quantity,

                requested_discount_percent=(
                    discount
                ),

                manual_review_required=False,
            )

        # =====================================================
        # 13. PRODUCT ACTIVE CHECK
        # =====================================================

        if hasattr(
            product,
            "is_active",
        ):

            if not product.is_active:

                return AgentChatResponse(
                    message=(
                        f"{product.name} is currently "
                        "inactive and cannot be ordered."
                    ),

                    intent="CREATE_ORDER",

                    merchant_id=(
                        request.merchant_id
                    ),

                    product_id=product.id,

                    product_name=product.name,

                    quantity=quantity,

                    requested_discount_percent=(
                        discount
                    ),

                    manual_review_required=False,
                )

        elif hasattr(
            product,
            "active",
        ):

            if not product.active:

                return AgentChatResponse(
                    message=(
                        f"{product.name} is currently "
                        "inactive and cannot be ordered."
                    ),

                    intent="CREATE_ORDER",

                    merchant_id=(
                        request.merchant_id
                    ),

                    product_id=product.id,

                    product_name=product.name,

                    quantity=quantity,

                    requested_discount_percent=(
                        discount
                    ),

                    manual_review_required=False,
                )

        # =====================================================
        # 14. STOCK CHECK
        # =====================================================

        if hasattr(
            product,
            "stock_quantity",
        ):

            stock = int(
                product.stock_quantity or 0
            )

        elif hasattr(
            product,
            "stock",
        ):

            stock = int(
                product.stock or 0
            )

        else:

            raise HTTPException(
                status_code=500,
                detail="Product stock field not found",
            )

        # =====================================================
        # 15. OUT OF STOCK
        # =====================================================

        if stock <= 0:

            return AgentChatResponse(
                message=(
                    f"{product.name} is currently "
                    "out of stock."
                ),

                intent="CREATE_ORDER",

                merchant_id=(
                    request.merchant_id
                ),

                product_id=product.id,

                product_name=product.name,

                quantity=quantity,

                requested_discount_percent=(
                    discount
                ),

                manual_review_required=False,
            )

        # =====================================================
        # 16. INSUFFICIENT STOCK
        # =====================================================

        if stock < quantity:

            return AgentChatResponse(
                message=(
                    f"{product.name} does not have "
                    f"enough inventory.\n\n"
                    f"Available stock: {stock}\n"
                    f"Requested quantity: {quantity}"
                ),

                intent="CREATE_ORDER",

                merchant_id=(
                    request.merchant_id
                ),

                product_id=product.id,

                product_name=product.name,

                quantity=quantity,

                requested_discount_percent=(
                    discount
                ),

                manual_review_required=False,
            )

        # =====================================================
        # 17. BUILD ORDER REQUEST
        # =====================================================

        order_request = OrderCreate(
            merchant_id=request.merchant_id,

            product_id=product.id,

            quantity=quantity,

            requested_discount_percent=(
                discount
            ),
        )

        # =====================================================
        # 18. CREATE ORDER
        # =====================================================
        #
        # The agent does NOT directly:
        #
        # - process Razorpay payment
        # - authorize money movement
        # - calculate independent risk
        # - manually modify stock
        # - create audit logs
        #
        # The existing order pipeline handles those.
        #
        # =====================================================

        order_result = await create_order_internal(
            request=order_request,
            db=db,
        )

        # -----------------------------------------------------
        # IMPORTANT:
        # create_order_internal() can return JSONResponse.
        # Never access order.status directly here.
        # -----------------------------------------------------

        order_data = normalize_order_result(
            order_result
        )

        # =====================================================
        # 19. FINAL ORDER STATUS
        # =====================================================

        order_status = str(
            order_value(
                order_data,
                "status",
                "",
            )
            or ""
        ).upper()

        manual_review_required = (
            order_status
            == "MANUAL_REVIEW_REQUIRED"
        )

        payment_approved = (
            order_status == "APPROVED"
        )

        # =====================================================
        # 20. ORDER VALUES
        # =====================================================

        order_id = order_value(
            order_data,
            "id",
        )

        order_quantity = safe_int(
            order_value(
                order_data,
                "quantity",
                quantity,
            ),
            quantity,
        )

        original_amount = safe_float(
            order_value(
                order_data,
                "original_amount",
                0,
            )
        )

        final_amount = safe_float(
            order_value(
                order_data,
                "final_amount",
                0,
            )
        )

        approved_discount = safe_float(
            order_value(
                order_data,
                "discount_percent",
                0,
            )
        )

        risk_score = safe_float(
            order_value(
                order_data,
                "risk_score",
                0,
            )
        )

        risk_level = str(
            order_value(
                order_data,
                "risk_level",
                "LOW",
            )
            or "LOW"
        ).upper()

        # =====================================================
        # 21. APPROVED RESPONSE
        # =====================================================

        if payment_approved:

            response_message = (
                f"{product.name} order was "
                f"automatically approved.\n\n"

                f"Quantity: {order_quantity}\n"

                f"Requested discount: "
                f"{discount:.2f}%\n"

                f"Approved discount: "
                f"{approved_discount:.2f}%\n"

                f"Original amount: "
                f"₹{original_amount:.2f}\n"

                f"Final amount: "
                f"₹{final_amount:.2f}\n"

                f"Risk: {risk_level} "
                f"({risk_score:.0f})\n"

                f"Order ID: {order_id}\n\n"

                "Human confirmation is still required "
                "before opening Razorpay checkout."
            )

        # =====================================================
        # 22. MANUAL REVIEW RESPONSE
        # =====================================================

        elif manual_review_required:

            response_message = (
                f"{product.name} order was created "
                f"but requires manual review.\n\n"

                f"Quantity: {order_quantity}\n"

                f"Requested discount: "
                f"{discount:.2f}%\n"

                f"Approved discount: "
                f"{approved_discount:.2f}%\n"

                f"Original amount: "
                f"₹{original_amount:.2f}\n"

                f"Final amount: "
                f"₹{final_amount:.2f}\n"

                f"Risk: {risk_level} "
                f"({risk_score:.0f})\n"

                f"Order ID: {order_id}"
            )

        # =====================================================
        # 23. OTHER ORDER STATUS
        # =====================================================

        else:

            response_message = (
                f"{product.name} order was created.\n\n"

                f"Quantity: {order_quantity}\n"

                f"Requested discount: "
                f"{discount:.2f}%\n"

                f"Approved discount: "
                f"{approved_discount:.2f}%\n"

                f"Original amount: "
                f"₹{original_amount:.2f}\n"

                f"Final amount: "
                f"₹{final_amount:.2f}\n"

                f"Risk: {risk_level} "
                f"({risk_score:.0f})\n"

                f"Order status: {order_status}\n"

                f"Order ID: {order_id}"
            )

        # =====================================================
        # 24. RETURN RESPONSE
        # =====================================================

        return AgentChatResponse(
            message=response_message,

            intent="CREATE_ORDER",

            merchant_id=(
                request.merchant_id
            ),

            product_id=product.id,

            product_name=product.name,

            quantity=order_quantity,

            requested_discount_percent=(
                discount
            ),

            original_amount=(
                original_amount
            ),

            final_amount=(
                final_amount
            ),

            approved_discount_percent=(
                approved_discount
            ),

            risk_score=risk_score,

            risk_level=risk_level,

            order_id=order_id,

            order_status=order_status,

            manual_review_required=(
                manual_review_required
            ),
        )

    # =========================================================
    # HTTP EXCEPTION
    # =========================================================

    except HTTPException:

        db.rollback()

        raise

    # =========================================================
    # UNEXPECTED ERROR
    # =========================================================

    except Exception as e:

        db.rollback()

        print(
            "========================================"
        )

        print(
            "AGENT CHAT ERROR:"
        )

        print(
            repr(e)
        )

        print(
            "========================================"
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Agent chat request failed",
                "error": str(e),
            },
        )