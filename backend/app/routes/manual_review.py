from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.orm import Session

from app.db.database import get_db

from app.models.manual_review import (
    ManualReview,
    PENDING,
    APPROVED,
    REJECTED,
)

from app.models.order import Order
from app.models.product import Product
from app.models.audit_log import AuditLog

from app.schemas.manual_review import (
    ManualReviewResponse,
    ManualReviewDecision,
)

from app.routes.events import broadcast_event

# =========================================================
# AUTHENTICATION / AUTHORIZATION
# =========================================================
#
# Authentication:
#     get_current_user verifies the JWT and returns the
#     authenticated user.
#
# Authorization:
#     require_admin allows only users with admin role.
#
# IMPORTANT:
#     If your actual authentication dependency is located
#     somewhere else, change only this import.
#
# =========================================================

from app.auth.dependencies import (
    get_current_user,
)

from app.models.user import User


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/manual-reviews",
    tags=["Manual Reviews"],
)


# =========================================================
# CONSTANTS
# =========================================================

ADMIN_ROLES = {
    "ADMIN",
    "admin",
}

# Merchant users are also authorized to review orders
# belonging to their own merchant account.
MANUAL_REVIEW_ROLES = ADMIN_ROLES | {
    "MERCHANT",
    "merchant",
}


# =========================================================
# UTC NOW
# =========================================================

def utc_now():
    """
    Return a timezone-aware UTC datetime.

    If your SQLAlchemy DateTime columns are timezone-naive,
    replace this with:

        datetime.utcnow()
    """

    return datetime.now(timezone.utc)


# =========================================================
# AUTHENTICATION
# =========================================================

def require_authenticated_user(
    current_user: User = Depends(
        get_current_user
    ),
) -> User:
    """
    Authentication dependency.

    A valid JWT is required.

    The actual JWT validation is performed by
    get_current_user.
    """

    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    return current_user


# =========================================================
# AUTHORIZATION - ADMIN
# =========================================================

def require_admin(
    current_user: User = Depends(
        require_authenticated_user
    ),
) -> User:
    """
    Authorization dependency.

    ADMIN users can review any permitted merchant order.
    MERCHANT users can review orders belonging to their
    own merchant account.
    """

    role = str(
        getattr(
            current_user,
            "role",
            "",
        )
        or ""
    ).strip()

    if role not in MANUAL_REVIEW_ROLES:

        raise HTTPException(
            status_code=403,
            detail=(
                "Merchant or admin authorization required "
                "for manual review operations."
            ),
        )

    return current_user


# =========================================================
# HELPER - GET USER ID
# =========================================================

def get_user_id(
    user: User,
):
    """
    Safely extract authenticated user ID.
    """

    return getattr(
        user,
        "id",
        None,
    )


# =========================================================
# HELPER - GET USER MERCHANT ID
# =========================================================

def get_user_merchant_id(
    user: User,
):
    """
    Safely extract merchant_id from authenticated user.

    Returns None when the user is a global/admin account
    without merchant ownership information.
    """

    merchant_id = getattr(
        user,
        "merchant_id",
        None,
    )

    if merchant_id is None:
        return None

    try:
        return int(merchant_id)

    except (
        TypeError,
        ValueError,
    ):
        return None


# =========================================================
# HELPER - MERCHANT AUTHORIZATION
# =========================================================

def authorize_merchant_access(
    user: User,
    merchant_id: int,
):
    """
    Prevent an authenticated admin belonging to one merchant
    from accessing another merchant's manual reviews.

    If the User model does not contain merchant_id,
    this function allows the authenticated ADMIN through.

    This supports a global admin model.

    If your application requires every admin to belong to
    exactly one merchant, remove the None bypass and enforce
    merchant_id equality.
    """

    user_merchant_id = (
        get_user_merchant_id(user)
    )

    # -----------------------------------------------------
    # GLOBAL ADMIN
    # -----------------------------------------------------

    if user_merchant_id is None:
        return

    # -----------------------------------------------------
    # MERCHANT ADMIN
    # -----------------------------------------------------

    if int(user_merchant_id) != int(
        merchant_id
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "You are not authorized to access "
                "this merchant's manual review."
            ),
        )


# =========================================================
# GET ALL MANUAL REVIEWS
# =========================================================

@router.get(
    "/",
    response_model=list[ManualReviewResponse],
)
def get_manual_reviews(
    status: str | None = None,
    merchant_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_authenticated_user
    ),
):
    """
    Get manual reviews.

    Authentication:
        Required.

    Authorization:
        Authenticated users may read reviews.

        If the authenticated user has merchant_id,
        only that merchant's reviews are returned.

        A global user without merchant_id can query
        specific merchant_id values.

    Examples:

        GET /manual-reviews/

        GET /manual-reviews/?status=PENDING

        GET /manual-reviews/?merchant_id=1

        GET /manual-reviews/?status=PENDING&merchant_id=1
    """

    try:

        query = db.query(
            ManualReview
        )

        # =================================================
        # STATUS FILTER
        # =================================================

        if status:

            normalized_status = (
                status
                .strip()
                .upper()
            )

            if normalized_status not in {
                PENDING,
                APPROVED,
                REJECTED,
            }:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Invalid status. "
                        "Use PENDING, APPROVED or REJECTED."
                    ),
                )

            query = query.filter(
                ManualReview.status
                == normalized_status
            )

        # =================================================
        # MERCHANT AUTHORIZATION
        # =================================================

        user_merchant_id = (
            get_user_merchant_id(
                current_user
            )
        )

        # -------------------------------------------------
        # USER BELONGS TO A MERCHANT
        # -------------------------------------------------

        if user_merchant_id is not None:

            # Ignore arbitrary merchant_id supplied by
            # the frontend and force the authenticated
            # merchant.

            query = query.filter(
                ManualReview.merchant_id
                == user_merchant_id
            )

        # -------------------------------------------------
        # GLOBAL ADMIN
        # -------------------------------------------------

        elif merchant_id is not None:

            query = query.filter(
                ManualReview.merchant_id
                == merchant_id
            )

        # =================================================
        # FETCH
        # =================================================

        reviews = (
            query
            .order_by(
                ManualReview.created_at.desc()
            )
            .all()
        )

        return reviews

    except HTTPException:

        raise

    except Exception as e:

        print(
            "GET MANUAL REVIEWS ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Unable to fetch manual reviews"
                ),
                "error": str(e),
            },
        )


# =========================================================
# PUBLIC ORDER STATUS FOR BUYER AGENT
# =========================================================
#
# This endpoint is READ-ONLY. It does not expose manual-review
# decision controls and cannot approve/reject anything.
# It exists only so the public buyer Agent can detect when the
# merchant has approved/rejected an Agent-created order.
#
# IMPORTANT:
# Keep this endpoint BEFORE /{review_id}.
# =========================================================

@router.get(
    "/order-status/{order_id}",
)
def get_buyer_order_status(
    order_id: int,
    db: Session = Depends(get_db),
):
    try:
        order = (
            db.query(Order)
            .filter(Order.id == order_id)
            .first()
        )

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        # Return only the minimum state needed by the buyer Agent.
        # No merchant/user information or review controls are exposed.
        return {
            "order_id": order.id,
            "status": str(order.status or "").upper(),
            "order_status": str(order.status or "").upper(),
            "payment_approved": bool(
                getattr(order, "payment_approved", False)
            ),
            "payment_gate_status": getattr(
                order,
                "payment_gate_status",
                None,
            ),
            "manual_review_required": bool(
                getattr(
                    order,
                    "manual_review_required",
                    False,
                )
            ),
            "payment_required": bool(
                getattr(
                    order,
                    "payment_required",
                    True,
                )
            ),
        }

    except HTTPException:
        raise

    except Exception as e:
        print(
            "GET BUYER ORDER STATUS ERROR:",
            repr(e),
        )
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to fetch order status",
                "error": str(e),
            },
        )


# =========================================================
# GET SINGLE MANUAL REVIEW
# =========================================================

@router.get(
    "/{review_id}",
    response_model=ManualReviewResponse,
)
def get_manual_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_authenticated_user
    ),
):
    """
    Get one manual review.

    Authentication:
        Required.

    Authorization:
        Merchant users can only see reviews belonging
        to their merchant.
    """

    try:

        # =================================================
        # FETCH REVIEW
        # =================================================

        review = (
            db.query(
                ManualReview
            )
            .filter(
                ManualReview.id
                == review_id
            )
            .first()
        )

        if not review:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Manual review not found"
                ),
            )

        # =================================================
        # MERCHANT AUTHORIZATION
        # =================================================

        authorize_merchant_access(
            current_user,
            review.merchant_id,
        )

        return review

    except HTTPException:

        raise

    except Exception as e:

        print(
            "GET MANUAL REVIEW ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Unable to fetch manual review"
                ),
                "error": str(e),
            },
        )


# =========================================================
# APPROVE / REJECT MANUAL REVIEW
# =========================================================

@router.post(
    "/{review_id}/decision",
    response_model=ManualReviewResponse,
)
async def decide_manual_review(
    review_id: int,
    request: ManualReviewDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_admin
    ),
):
    """
    Human manual-review decision endpoint.

    ======================================================
    AUTHENTICATION
    ======================================================

    A valid JWT is required.

    ======================================================
    AUTHORIZATION
    ======================================================

    ADMIN users can approve/reject any permitted review.
    MERCHANT users can approve/reject reviews belonging to
    their own merchant account.

    ======================================================
    APPROVE
    ======================================================

        ManualReview -> APPROVED
        Order        -> APPROVED
        Payment      -> allowed
        Inventory    -> deducted once

    ======================================================
    REJECT
    ======================================================

        ManualReview -> REJECTED
        Order        -> REJECTED
        Payment      -> blocked
        Inventory    -> unchanged

    ======================================================
    IMPORTANT
    ======================================================

    reviewed_by is NOT trusted from the frontend.

    The authenticated user's identity is used instead.
    """

    try:

        # =================================================
        # 1. AUTHENTICATION
        # =================================================
        #
        # require_admin already guarantees:
        #
        #   JWT exists
        #   JWT is valid
        #   user exists
        #   user has ADMIN or MERCHANT role
        #
        # =================================================

        authenticated_user_id = (
            get_user_id(
                current_user
            )
        )

        authenticated_user_name = (
            getattr(
                current_user,
                "name",
                None,
            )
            or getattr(
                current_user,
                "email",
                None,
            )
            or (
                f"USER-{authenticated_user_id}"
                if authenticated_user_id is not None
                else "ADMIN"
            )
        )

        authenticated_user_name = str(
            authenticated_user_name
        ).strip()

        if not authenticated_user_name:
            authenticated_user_name = "ADMIN"

        print()
        print("=" * 70)
        print("MANUAL REVIEW DECISION")
        print("=" * 70)

        print(
            f"Authenticated user ID: "
            f"{authenticated_user_id}"
        )

        print(
            f"Authenticated user: "
            f"{authenticated_user_name}"
        )

        print(
            f"Authenticated role: "
            f"{getattr(current_user, 'role', None)}"
        )

        print(
            f"Review ID: {review_id}"
        )

        print("=" * 70)

        # =================================================
        # 2. VALIDATE ACTION
        # =================================================

        raw_action = getattr(
            request,
            "action",
            None,
        )

        if hasattr(
            raw_action,
            "value",
        ):

            action = str(
                raw_action.value
            ).upper().strip()

        else:

            action = str(
                raw_action or ""
            ).upper().strip()

        # -------------------------------------------------
        # APPROVE / APPROVED
        # -------------------------------------------------

        if action == "APPROVED":

            action = "APPROVE"

        # -------------------------------------------------
        # REJECT / REJECTED
        # -------------------------------------------------

        if action == "REJECTED":

            action = "REJECT"

        if action not in {
            "APPROVE",
            "REJECT",
        }:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid review action. "
                    "Use APPROVE or REJECT."
                ),
            )

        # =================================================
        # 3. LOCK MANUAL REVIEW
        # =================================================

        review = (
            db.query(
                ManualReview
            )
            .filter(
                ManualReview.id
                == review_id
            )
            .with_for_update()
            .first()
        )

        if not review:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Manual review not found"
                ),
            )

        # =================================================
        # 4. MERCHANT AUTHORIZATION
        # =================================================

        authorize_merchant_access(
            current_user,
            review.merchant_id,
        )

        # =================================================
        # 5. REVIEW MUST BE PENDING
        # =================================================

        current_review_status = str(
            review.status or ""
        ).upper().strip()

        if current_review_status != PENDING:

            raise HTTPException(
                status_code=409,
                detail={
                    "message": (
                        "Review has already been processed."
                    ),
                    "review_id": review.id,
                    "current_status": review.status,
                },
            )

        # =================================================
        # 6. LOCK ORDER
        # =================================================

        order = (
            db.query(
                Order
            )
            .filter(
                Order.id
                == review.order_id
            )
            .with_for_update()
            .first()
        )

        if not order:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Associated order not found"
                ),
            )

        # =================================================
        # 7. ADDITIONAL MERCHANT CHECK
        # =================================================

        if (
            review.merchant_id
            != order.merchant_id
        ):

            raise HTTPException(
                status_code=409,
                detail=(
                    "Manual review merchant does not "
                    "match the order merchant."
                ),
            )

        authorize_merchant_access(
            current_user,
            order.merchant_id,
        )

        # =================================================
        # 8. LOCK PRODUCT
        # =================================================

        product = (
            db.query(
                Product
            )
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
                    "Associated product not found"
                ),
            )

        # =================================================
        # 9. PRODUCT MERCHANT CHECK
        # =================================================

        product_merchant_id = getattr(
            product,
            "merchant_id",
            None,
        )

        if (
            product_merchant_id is not None
            and int(product_merchant_id)
            != int(order.merchant_id)
        ):

            raise HTTPException(
                status_code=409,
                detail=(
                    "Product merchant does not "
                    "match the order merchant."
                ),
            )

        # =================================================
        # 10. OLD STATUS
        # =================================================

        old_order_status = str(
            order.status or ""
        )

        old_review_status = str(
            review.status or ""
        )

        # =================================================
        # 11. REVIEW COMMENT
        # =================================================

        review_comment = (
            str(
                getattr(
                    request,
                    "review_comment",
                    None,
                )
                or ""
            )
            .strip()
            or None
        )

        # =================================================
        # IMPORTANT:
        #
        # DO NOT TRUST request.reviewed_by
        #
        # The reviewer comes from JWT-authenticated user.
        # =================================================

        reviewed_by = (
            authenticated_user_name
        )

        # =================================================
        # 12. DETERMINE STOCK FIELD
        # =================================================

        if hasattr(
            product,
            "stock_quantity",
        ):

            current_stock = int(
                product.stock_quantity
                or 0
            )

            stock_field = (
                "stock_quantity"
            )

        elif hasattr(
            product,
            "stock",
        ):

            current_stock = int(
                product.stock
                or 0
            )

            stock_field = "stock"

        else:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Product stock field "
                    "was not found."
                ),
            )

        # =================================================
        # 13. ORDER QUANTITY
        # =================================================

        quantity = int(
            getattr(
                order,
                "quantity",
                0,
            )
            or 0
        )

        if quantity <= 0:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Order quantity must be "
                    "greater than zero."
                ),
            )

        # =================================================
        # 14. COMMON FLAGS
        # =================================================

        inventory_already_deducted = bool(
            getattr(
                order,
                "inventory_deducted",
                False,
            )
        )

        remaining_stock = (
            current_stock
        )

        # =================================================
        # 15. APPROVE
        # =================================================

        if action == "APPROVE":

            # -------------------------------------------------
            # PRODUCT ACTIVE CHECK
            # -------------------------------------------------

            if hasattr(
                product,
                "is_active",
            ):

                if not bool(
                    product.is_active
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Product is inactive "
                            "and cannot be approved."
                        ),
                    )

            elif hasattr(
                product,
                "active",
            ):

                if not bool(
                    product.active
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Product is inactive "
                            "and cannot be approved."
                        ),
                    )

            # -------------------------------------------------
            # MERCHANT SAFETY
            # -------------------------------------------------

            merchant = getattr(
                product,
                "merchant",
                None,
            )

            if merchant:

                merchant_is_active = getattr(
                    merchant,
                    "is_active",
                    True,
                )

                if not bool(
                    merchant_is_active
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Merchant is inactive "
                            "and cannot approve "
                            "this order."
                        ),
                    )

            # -------------------------------------------------
            # INVENTORY
            # -------------------------------------------------

            if inventory_already_deducted:

                remaining_stock = (
                    current_stock
                )

                inventory_message = (
                    "Inventory was already deducted "
                    "for this order. No second "
                    "deduction was performed."
                )

            else:

                if current_stock < quantity:

                    raise HTTPException(
                        status_code=400,
                        detail={
                            "message": (
                                "Insufficient stock "
                                "for manual review "
                                "approval."
                            ),
                            "available": (
                                current_stock
                            ),
                            "required": quantity,
                            "product_id": (
                                order.product_id
                            ),
                            "order_id": (
                                order.id
                            ),
                        },
                    )

                remaining_stock = (
                    current_stock
                    - quantity
                )

                if remaining_stock < 0:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Inventory cannot "
                            "become negative."
                        ),
                    )

                # ---------------------------------------------
                # UPDATE STOCK
                # ---------------------------------------------

                if stock_field == "stock_quantity":

                    product.stock_quantity = (
                        remaining_stock
                    )

                else:

                    product.stock = (
                        remaining_stock
                    )

                # ---------------------------------------------
                # MARK INVENTORY DEDUCTED
                # ---------------------------------------------

                if hasattr(
                    order,
                    "inventory_deducted",
                ):

                    order.inventory_deducted = True

                inventory_message = (
                    f"{quantity} unit(s) "
                    "were deducted from inventory."
                )

            # -------------------------------------------------
            # MANUAL REVIEW
            # -------------------------------------------------

            review.status = (
                APPROVED
            )

            # -------------------------------------------------
            # ORDER
            # -------------------------------------------------

            order.status = (
                "APPROVED"
            )

            # -------------------------------------------------
            # PAYMENT
            # -------------------------------------------------

            if hasattr(
                order,
                "payment_approved",
            ):

                order.payment_approved = True

            # -------------------------------------------------
            # REVIEW FLAG
            # -------------------------------------------------

            if hasattr(
                order,
                "manual_review_required",
            ):

                order.manual_review_required = (
                    False
                )

            # -------------------------------------------------
            # AUDIT EVENT
            # -------------------------------------------------

            audit_event_type = (
                "MANUAL_REVIEW_APPROVED"
            )

            audit_message = (
                "Manual review approved by "
                f"{reviewed_by}. "
                + inventory_message
            )

            event_message = (
                "Manual review approved successfully."
            )

        # =================================================
        # 16. REJECT
        # =================================================

        else:

            # -------------------------------------------------
            # INVENTORY MUST NOT CHANGE
            # -------------------------------------------------

            remaining_stock = (
                current_stock
            )

            # -------------------------------------------------
            # MANUAL REVIEW
            # -------------------------------------------------

            review.status = (
                REJECTED
            )

            # -------------------------------------------------
            # ORDER
            # -------------------------------------------------

            order.status = (
                "REJECTED"
            )

            # -------------------------------------------------
            # PAYMENT
            # -------------------------------------------------

            if hasattr(
                order,
                "payment_approved",
            ):

                order.payment_approved = (
                    False
                )

            # -------------------------------------------------
            # REVIEW FLAG
            # -------------------------------------------------

            if hasattr(
                order,
                "manual_review_required",
            ):

                order.manual_review_required = (
                    False
                )

            # -------------------------------------------------
            # AUDIT EVENT
            # -------------------------------------------------

            audit_event_type = (
                "MANUAL_REVIEW_REJECTED"
            )

            audit_message = (
                "Manual review rejected by "
                f"{reviewed_by}. "
                "No inventory adjustment was required."
            )

            event_message = (
                "Manual review rejected."
            )

        # =================================================
        # 17. REVIEW INFORMATION
        # =================================================

        review.reviewed_by = (
            reviewed_by
        )

        review.review_comment = (
            review_comment
        )

        review.reviewed_at = (
            utc_now()
        )

        # =================================================
        # 18. OPTIONAL ORDER AUDIT FIELDS
        # =================================================

        if hasattr(
            order,
            "audit_event_type",
        ):

            order.audit_event_type = (
                audit_event_type
            )

        if hasattr(
            order,
            "audit_performed_by",
        ):

            order.audit_performed_by = (
                reviewed_by
            )

        # =================================================
        # 19. CREATE AUDIT LOG
        # =================================================

        audit_log = AuditLog(

            order_id=order.id,

            merchant_id=order.merchant_id,

            event_type=audit_event_type,

            message=audit_message,

            old_status=old_order_status,

            new_status=order.status,

            risk_score=review.risk_score,

            risk_level=review.risk_level,

            performed_by=reviewed_by,
        )

        db.add(
            audit_log
        )

        # =================================================
        # 20. FLUSH
        # =================================================

        db.flush()

        # =================================================
        # 21. COMMIT
        # =================================================

        db.commit()

        # =================================================
        # 22. REFRESH
        # =================================================

        db.refresh(
            review
        )

        db.refresh(
            order
        )

        db.refresh(
            product
        )

        # =================================================
        # 23. EVENT DATA
        # =================================================

        event_data = {

            "review_id": (
                review.id
            ),

            "order_id": (
                order.id
            ),

            "merchant_id": (
                order.merchant_id
            ),

            "product_id": (
                order.product_id
            ),

            "quantity": (
                quantity
            ),

            "review_status": (
                review.status
            ),

            "order_status": (
                order.status
            ),

            "old_order_status": (
                old_order_status
            ),

            "old_review_status": (
                old_review_status
            ),

            "risk_score": (
                float(
                    review.risk_score
                )
                if review.risk_score is not None
                else None
            ),

            "risk_level": (
                review.risk_level
            ),

            "reason": (
                review.reason
            ),

            "reviewed_by": (
                review.reviewed_by
            ),

            "reviewer_user_id": (
                authenticated_user_id
            ),

            "reviewer_role": (
                getattr(
                    current_user,
                    "role",
                    None,
                )
            ),

            "review_comment": (
                review.review_comment
            ),

            "reviewed_at": (
                review.reviewed_at.isoformat()
                if review.reviewed_at
                else None
            ),

            "remaining_stock": int(
                remaining_stock
            ),

            "inventory_deducted": bool(
                getattr(
                    order,
                    "inventory_deducted",
                    False,
                )
            ),

            "payment_approved": bool(
                getattr(
                    order,
                    "payment_approved",
                    False,
                )
            ),

            "manual_review_required": bool(
                getattr(
                    order,
                    "manual_review_required",
                    False,
                )
            ),

            "message": (
                event_message
            ),
        }

        # =================================================
        # 24. BROADCAST SSE EVENT
        # =================================================

        try:

            await broadcast_event(
                "manual_review_decision",
                event_data,
            )

        except Exception as event_error:

            # IMPORTANT:
            #
            # Database transaction has already committed.
            #
            # SSE failure must NOT undo the human decision.

            print(
                "SSE MANUAL REVIEW ERROR:",
                repr(event_error),
            )

        # =================================================
        # 25. LOG SUCCESS
        # =================================================

        print()
        print("=" * 70)
        print("MANUAL REVIEW DECISION COMPLETE")
        print("=" * 70)

        print(
            f"Review ID: {review.id}"
        )

        print(
            f"Action: {action}"
        )

        print(
            f"Reviewer ID: "
            f"{authenticated_user_id}"
        )

        print(
            f"Reviewer: {reviewed_by}"
        )

        print(
            f"Role: "
            f"{getattr(current_user, 'role', None)}"
        )

        print(
            f"Order ID: {order.id}"
        )

        print(
            f"Order status: {order.status}"
        )

        print(
            f"Review status: {review.status}"
        )

        print(
            f"Remaining stock: "
            f"{remaining_stock}"
        )

        print("=" * 70)

        # =================================================
        # 26. RETURN
        # =================================================

        return review

    # =====================================================
    # HTTP ERROR
    # =====================================================

    except HTTPException:

        try:
            db.rollback()

        except Exception:
            pass

        raise

    # =====================================================
    # UNEXPECTED ERROR
    # =====================================================

    except Exception as e:

        try:
            db.rollback()

        except Exception:
            pass

        print()
        print("=" * 70)
        print(
            "MANUAL REVIEW DECISION ERROR"
        )
        print("=" * 70)

        print(
            f"Error type: "
            f"{type(e).__name__}"
        )

        print(
            f"Error: {e}"
        )

        print("=" * 70)

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Manual review decision failed"
                ),
                "error": str(e),
            },
        )