from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import get_db

from app.models.merchant import Merchant
from app.models.product import Product
from app.models.user import User

from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
)

from app.auth.dependencies import get_current_user


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


# =========================================================
# AUTHORIZATION HELPERS
# =========================================================

def get_user_role(user: User) -> str:
    """
    Safely get the user's role.

    Expected roles:
        ADMIN
        MERCHANT

    Supports enum-style roles as well as strings.
    """

    role = getattr(
        user,
        "role",
        None,
    )

    if hasattr(role, "value"):
        role = role.value

    return str(
        role or ""
    ).upper().strip()


def require_authenticated_user(
    current_user: User = Depends(
        get_current_user
    ),
) -> User:
    """
    Authentication dependency.

    get_current_user is responsible for verifying
    the JWT/session and returning the logged-in user.
    """

    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    return current_user


def require_admin(
    current_user: User = Depends(
        get_current_user
    ),
) -> User:
    """
    Admin-only authorization.
    """

    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    role = get_user_role(current_user)

    if role != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Admin authorization required",
        )

    return current_user


def get_user_merchant_id(
    user: User,
) -> int | None:
    """
    Get merchant_id from the authenticated user.

    Supports:

        user.merchant_id

    or:

        user.merchant.id
    """

    merchant_id = getattr(
        user,
        "merchant_id",
        None,
    )

    if merchant_id is None:

        merchant = getattr(
            user,
            "merchant",
            None,
        )

        if merchant:
            merchant_id = getattr(
                merchant,
                "id",
                None,
            )

    if merchant_id is None:
        return None

    try:
        return int(merchant_id)
    except (TypeError, ValueError):
        return None


def authorize_merchant_product(
    product: Product,
    current_user: User,
):
    """
    Verify that the authenticated user can manage
    the specified product.

    ADMIN:
        Can manage every product.

    MERCHANT:
        Can manage only products belonging to
        their own merchant.
    """

    role = get_user_role(current_user)

    # -----------------------------------------------------
    # ADMIN
    # -----------------------------------------------------

    if role == "ADMIN":
        return

    # -----------------------------------------------------
    # MERCHANT
    # -----------------------------------------------------

    if role != "MERCHANT":
        raise HTTPException(
            status_code=403,
            detail=(
                "You are not authorized to manage products"
            ),
        )

    user_merchant_id = get_user_merchant_id(
        current_user
    )

    if user_merchant_id is None:
        raise HTTPException(
            status_code=403,
            detail=(
                "Authenticated user is not associated "
                "with a merchant"
            ),
        )

    if int(product.merchant_id) != int(
        user_merchant_id
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "You are not authorized to manage "
                "this merchant's product"
            ),
        )


# =========================================================
# PRODUCT SERIALIZATION HELPERS
# =========================================================

def calculate_margin_percent(
    price,
    cost_price,
) -> float:
    """
    Calculate product margin percentage.

    Margin % =
        ((price - cost_price) / price) * 100
    """

    try:
        price_value = float(price or 0)
    except (TypeError, ValueError):
        price_value = 0.0

    try:
        cost_value = float(cost_price or 0)
    except (TypeError, ValueError):
        cost_value = 0.0

    if price_value <= 0:
        return 0.0

    return round(
        (
            (
                price_value
                - cost_value
            )
            / price_value
        )
        * 100,
        2,
    )


def get_stock_status(
    stock_quantity,
) -> str:
    """
    Return normalized stock status.
    """

    try:
        quantity = int(
            stock_quantity or 0
        )
    except (TypeError, ValueError):
        quantity = 0

    if quantity <= 0:
        return "OUT_OF_STOCK"

    if quantity <= 5:
        return "LOW_STOCK"

    return "IN_STOCK"


def build_catalog_item(
    product: Product,
    include_cost_price: bool = False,
) -> dict:
    """
    Convert a Product SQLAlchemy object into a
    JSON-safe catalog dictionary.

    include_cost_price:
        Used by the internal AI catalog.

    Public buyer catalog does NOT expose cost_price.
    """

    try:
        price = float(
            product.price or 0
        )
    except (TypeError, ValueError):
        price = 0.0

    try:
        cost_price = float(
            product.cost_price or 0
        )
    except (TypeError, ValueError):
        cost_price = 0.0

    try:
        stock_quantity = int(
            product.stock_quantity or 0
        )
    except (TypeError, ValueError):
        stock_quantity = 0

    item = {
        "id": product.id,
        "product_id": product.id,

        "merchant_id": product.merchant_id,

        "name": product.name,

        "category": product.category,

        "description": product.description,

        "sku": product.sku,

        "price": price,

        "stock_quantity": stock_quantity,

        "stock_status": get_stock_status(
            stock_quantity
        ),

        "is_active": bool(
            product.is_active
        ),

        "margin_percent": calculate_margin_percent(
            price,
            cost_price,
        ),
    }

    if include_cost_price:
        item["cost_price"] = cost_price

    return item


# =========================================================
# CREATE PRODUCT
# =========================================================

@router.post(
    "/",
    response_model=ProductResponse,
    status_code=201,
)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_authenticated_user
    ),
):

    try:

        role = get_user_role(
            current_user
        )

        # -------------------------------------------------
        # AUTHORIZATION
        # -------------------------------------------------

        requested_merchant_id = (
            product_data.merchant_id
        )

        user_merchant_id = get_user_merchant_id(
            current_user
        )

        # -------------------------------------------------
        # ADMIN
        # -------------------------------------------------

        if role == "ADMIN":

            merchant_id = requested_merchant_id

        # -------------------------------------------------
        # MERCHANT
        # -------------------------------------------------

        elif role == "MERCHANT":

            if user_merchant_id is None:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Authenticated user is not "
                        "associated with a merchant"
                    ),
                )

            if int(requested_merchant_id) != int(
                user_merchant_id
            ):
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "You cannot create a product "
                        "for another merchant"
                    ),
                )

            merchant_id = user_merchant_id

        # -------------------------------------------------
        # OTHER ROLES
        # -------------------------------------------------

        else:

            raise HTTPException(
                status_code=403,
                detail=(
                    "You are not authorized "
                    "to create products"
                ),
            )

        # -------------------------------------------------
        # CHECK MERCHANT
        # -------------------------------------------------

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
                detail="Merchant not found",
            )

        # -------------------------------------------------
        # CHECK MERCHANT ACTIVE
        # -------------------------------------------------

        if hasattr(
            merchant,
            "is_active",
        ):

            if not bool(
                merchant.is_active
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Merchant is inactive. "
                        "Cannot create product."
                    ),
                )

        # -------------------------------------------------
        # CHECK SKU
        # -------------------------------------------------

        existing_product = (
            db.query(Product)
            .filter(
                Product.sku
                == product_data.sku
            )
            .first()
        )

        if existing_product:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Product with this SKU already exists"
                ),
            )

        # -------------------------------------------------
        # CREATE PRODUCT
        # -------------------------------------------------

        product = Product(
            merchant_id=merchant_id,
            name=product_data.name,
            category=product_data.category,
            description=product_data.description,
            price=product_data.price,
            cost_price=product_data.cost_price,
            stock_quantity=product_data.stock_quantity,
            sku=product_data.sku,
            is_active=product_data.is_active,
        )

        db.add(product)

        db.commit()

        db.refresh(product)

        return product

    except HTTPException:

        db.rollback()

        raise

    except Exception as e:

        db.rollback()

        print(
            "CREATE PRODUCT ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to create product",
                "error": str(e),
            },
        )


# =========================================================
# GET ALL PRODUCTS
# =========================================================

@router.get(
    "/",
    response_model=list[ProductResponse],
)
def get_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_authenticated_user
    ),
):

    try:

        role = get_user_role(
            current_user
        )

        query = db.query(Product)

        # -------------------------------------------------
        # ADMIN
        # -------------------------------------------------

        if role == "ADMIN":

            pass

        # -------------------------------------------------
        # MERCHANT
        # -------------------------------------------------

        elif role == "MERCHANT":

            merchant_id = get_user_merchant_id(
                current_user
            )

            if merchant_id is None:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Authenticated user is not "
                        "associated with a merchant"
                    ),
                )

            query = query.filter(
                Product.merchant_id
                == merchant_id
            )

        # -------------------------------------------------
        # OTHER ROLES
        # -------------------------------------------------

        else:

            raise HTTPException(
                status_code=403,
                detail=(
                    "You are not authorized "
                    "to view products"
                ),
            )

        return (
            query
            .order_by(
                Product.id.desc()
            )
            .all()
        )

    except HTTPException:

        raise

    except Exception as e:

        db.rollback()

        print(
            "GET PRODUCTS ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to fetch products",
                "error": str(e),
            },
        )


# =========================================================
# AI CATALOG
# =========================================================

@router.get(
    "/ai-catalog",
)
def get_ai_catalog(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_authenticated_user
    ),
):

    try:

        role = get_user_role(
            current_user
        )

        query = (
            db.query(Product)
            .filter(
                Product.is_active == True
            )
        )

        # -------------------------------------------------
        # ADMIN
        # -------------------------------------------------

        if role == "ADMIN":

            pass

        # -------------------------------------------------
        # MERCHANT
        # -------------------------------------------------

        elif role == "MERCHANT":

            merchant_id = get_user_merchant_id(
                current_user
            )

            if merchant_id is None:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Authenticated user is not "
                        "associated with a merchant"
                    ),
                )

            query = query.filter(
                Product.merchant_id
                == merchant_id
            )

        # -------------------------------------------------
        # OTHER ROLES
        # -------------------------------------------------

        else:

            raise HTTPException(
                status_code=403,
                detail=(
                    "You are not authorized "
                    "to access the AI catalog"
                ),
            )

        products = (
            query
            .order_by(
                Product.category.asc(),
                Product.name.asc(),
            )
            .all()
        )

        catalog = [
            build_catalog_item(
                product,
                include_cost_price=True,
            )
            for product in products
        ]

        return {
            "catalog": catalog,
            "products": catalog,
            "total_products": len(catalog),
        }

    except HTTPException:

        raise

    except Exception as e:

        db.rollback()

        print(
            "AI CATALOG ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Unable to fetch AI catalog"
                ),
                "error": str(e),
            },
        )


# =========================================================
# PUBLIC BUYER CATALOG
# =========================================================
#
# Buyer-facing, read-only catalog.
#
# IMPORTANT:
#   - NO authentication required
#   - ALL active merchants
#   - ONLY active products
#   - ONLY products with stock > 0
#
# This endpoint is intentionally separate from GET /
# because GET / is merchant-authenticated.
#
# =========================================================

@router.get(
    "/public-catalog",
)
def get_public_buyer_catalog(
    db: Session = Depends(get_db),
):
    """
    Public marketplace catalog.

    This endpoint is intentionally unauthenticated because
    buyers/Agent.jsx need to discover products before login
    or checkout.

    The implementation deliberately avoids a Product/Merchant
    JOIN. This makes the endpoint easier to diagnose when a
    database/query problem causes the frontend to timeout.
    """

    print()
    print("==================================================")
    print("PUBLIC BUYER CATALOG REQUEST")
    print("==================================================")

    try:

        # -------------------------------------------------
        # STEP 0
        # DATABASE HEALTH CHECK
        # -------------------------------------------------
        #
        # If execution stops here, the problem is not the
        # catalog query. It is the database/session layer.
        # -------------------------------------------------

        print(
            "PUBLIC CATALOG: testing database connection..."
        )

        db.execute(
            text("SELECT 1")
        )

        print(
            "PUBLIC CATALOG: database connection OK"
        )

        # -------------------------------------------------
        # STEP 1
        # LOAD ACTIVE MERCHANT IDS
        # -------------------------------------------------

        print(
            "PUBLIC CATALOG: loading active merchants..."
        )

        merchant_query = (
            db.query(Merchant.id)
        )

        if hasattr(
            Merchant,
            "is_active",
        ):

            merchant_query = (
                merchant_query
                .filter(
                    Merchant.is_active == True
                )
            )

        active_merchant_rows = (
            merchant_query
            .all()
        )

        active_merchant_ids = []

        for row in active_merchant_rows:

            merchant_id = row[0]

            if merchant_id is None:
                continue

            try:
                active_merchant_ids.append(
                    int(merchant_id)
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

        print(
            "PUBLIC CATALOG: active merchants:",
            len(active_merchant_ids),
        )

        # -------------------------------------------------
        # NO ACTIVE MERCHANTS
        # -------------------------------------------------

        if not active_merchant_ids:

            print(
                "PUBLIC CATALOG: no active merchants"
            )

            response = {
                "catalog": [],
                "products": [],
                "total_products": 0,
                "total_merchants": 0,
            }

            print(
                "PUBLIC CATALOG: SUCCESS"
            )

            print(
                "=================================================="
            )

            return response

        # -------------------------------------------------
        # STEP 2
        # LOAD ACTIVE + IN-STOCK PRODUCTS
        # -------------------------------------------------
        #
        # IMPORTANT:
        # We do NOT join Merchant here.
        #
        # Product rows are filtered using the already loaded
        # merchant ID list.
        # -------------------------------------------------

        print(
            "PUBLIC CATALOG: querying products..."
        )

        product_query = (
            db.query(Product)
            .filter(
                Product.merchant_id.in_(
                    active_merchant_ids
                ),
                Product.is_active == True,
                Product.stock_quantity > 0,
            )
        )

        products = (
            product_query
            .order_by(
                Product.category.asc(),
                Product.name.asc(),
                Product.merchant_id.asc(),
                Product.id.asc(),
            )
            .all()
        )

        print(
            "PUBLIC CATALOG: products found:",
            len(products),
        )

        # -------------------------------------------------
        # STEP 3
        # BUILD JSON-SAFE CATALOG
        # -------------------------------------------------

        print(
            "PUBLIC CATALOG: building response..."
        )

        catalog = []

        for product in products:

            catalog.append(
                build_catalog_item(
                    product,
                    include_cost_price=False,
                )
            )

        # -------------------------------------------------
        # STEP 4
        # COUNT MERCHANTS PRESENT IN CATALOG
        # -------------------------------------------------

        catalog_merchant_ids = {
            item["merchant_id"]
            for item in catalog
            if item.get("merchant_id")
            is not None
        }

        total_merchants = len(
            catalog_merchant_ids
        )

        # -------------------------------------------------
        # STEP 5
        # FINAL RESPONSE
        # -------------------------------------------------

        response = {
            "catalog": catalog,
            "products": catalog,
            "total_products": len(catalog),
            "total_merchants": total_merchants,
        }

        print(
            "PUBLIC CATALOG: response products:",
            response["total_products"],
        )

        print(
            "PUBLIC CATALOG: response merchants:",
            response["total_merchants"],
        )

        print(
            "PUBLIC CATALOG: SUCCESS"
        )

        print(
            "=================================================="
        )

        return response

    except HTTPException:

        db.rollback()

        raise

    except Exception as e:

        db.rollback()

        print()
        print(
            "=================================================="
        )

        print(
            "PUBLIC CATALOG: ERROR"
        )

        print(
            "PUBLIC CATALOG ERROR TYPE:",
            type(e).__name__,
        )

        print(
            "PUBLIC CATALOG ERROR:",
            repr(e),
        )

        print(
            "=================================================="
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Unable to fetch public buyer catalog"
                ),
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )


# =========================================================
# GET PRODUCT BY ID
# =========================================================

@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_authenticated_user
    ),
):

    try:

        product = (
            db.query(Product)
            .filter(
                Product.id == product_id
            )
            .first()
        )

        if not product:

            raise HTTPException(
                status_code=404,
                detail="Product not found",
            )

        # -------------------------------------------------
        # AUTHORIZATION
        # -------------------------------------------------

        authorize_merchant_product(
            product,
            current_user,
        )

        return product

    except HTTPException:

        raise

    except Exception as e:

        db.rollback()

        print(
            "GET PRODUCT ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Unable to fetch product"
                ),
                "error": str(e),
            },
        )


# =========================================================
# UPDATE PRODUCT
# =========================================================

@router.put(
    "/{product_id}",
    response_model=ProductResponse,
)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_authenticated_user
    ),
):

    try:

        product = (
            db.query(Product)
            .filter(
                Product.id == product_id
            )
            .first()
        )

        if not product:

            raise HTTPException(
                status_code=404,
                detail="Product not found",
            )

        # -------------------------------------------------
        # CHECK CURRENT PRODUCT OWNERSHIP
        # -------------------------------------------------

        authorize_merchant_product(
            product,
            current_user,
        )

        role = get_user_role(
            current_user
        )

        update_data = (
            product_data.model_dump(
                exclude_unset=True
            )
        )

        # -------------------------------------------------
        # MERCHANT ID CHANGE
        # -------------------------------------------------

        if "merchant_id" in update_data:

            requested_merchant_id = (
                update_data["merchant_id"]
            )

            if requested_merchant_id is None:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "merchant_id cannot be null"
                    ),
                )

            # ---------------------------------------------
            # ONLY ADMIN CAN MOVE PRODUCT BETWEEN
            # MERCHANTS
            # ---------------------------------------------

            if role != "ADMIN":

                user_merchant_id = (
                    get_user_merchant_id(
                        current_user
                    )
                )

                if (
                    user_merchant_id is None
                    or int(
                        requested_merchant_id
                    )
                    != int(
                        user_merchant_id
                    )
                ):

                    raise HTTPException(
                        status_code=403,
                        detail=(
                            "Merchant users cannot "
                            "transfer products to "
                            "another merchant"
                        ),
                    )

            # ---------------------------------------------
            # CHECK NEW MERCHANT
            # ---------------------------------------------

            merchant = (
                db.query(Merchant)
                .filter(
                    Merchant.id
                    == requested_merchant_id
                )
                .first()
            )

            if not merchant:

                raise HTTPException(
                    status_code=404,
                    detail="Merchant not found",
                )

            # ---------------------------------------------
            # CHECK MERCHANT ACTIVE
            # ---------------------------------------------

            if hasattr(
                merchant,
                "is_active",
            ):

                if not bool(
                    merchant.is_active
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Cannot transfer product "
                            "to an inactive merchant"
                        ),
                    )

        # -------------------------------------------------
        # CHECK SKU
        # -------------------------------------------------

        if "sku" in update_data:

            requested_sku = update_data["sku"]

            if requested_sku is None:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Product SKU cannot be null"
                    ),
                )

            existing_product = (
                db.query(Product)
                .filter(
                    Product.sku
                    == requested_sku,
                    Product.id
                    != product_id,
                )
                .first()
            )

            if existing_product:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Product with this SKU "
                        "already exists"
                    ),
                )

        # -------------------------------------------------
        # PRICE VALIDATION
        # -------------------------------------------------

        if "price" in update_data:

            if (
                update_data["price"]
                is not None
            ):

                try:

                    if float(
                        update_data["price"]
                    ) < 0:

                        raise HTTPException(
                            status_code=400,
                            detail=(
                                "Product price "
                                "cannot be negative"
                            ),
                        )

                except (
                    TypeError,
                    ValueError,
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Product price "
                            "must be a valid number"
                        ),
                    )

        # -------------------------------------------------
        # COST PRICE VALIDATION
        # -------------------------------------------------

        if "cost_price" in update_data:

            if (
                update_data["cost_price"]
                is not None
            ):

                try:

                    if float(
                        update_data["cost_price"]
                    ) < 0:

                        raise HTTPException(
                            status_code=400,
                            detail=(
                                "Product cost price "
                                "cannot be negative"
                            ),
                        )

                except (
                    TypeError,
                    ValueError,
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Product cost price "
                            "must be a valid number"
                        ),
                    )

        # -------------------------------------------------
        # STOCK VALIDATION
        # -------------------------------------------------

        if "stock_quantity" in update_data:

            if (
                update_data["stock_quantity"]
                is not None
            ):

                try:

                    if int(
                        update_data[
                            "stock_quantity"
                        ]
                    ) < 0:

                        raise HTTPException(
                            status_code=400,
                            detail=(
                                "Stock quantity "
                                "cannot be negative"
                            ),
                        )

                except (
                    TypeError,
                    ValueError,
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Stock quantity "
                            "must be a valid integer"
                        ),
                    )

        # -------------------------------------------------
        # UPDATE
        # -------------------------------------------------

        for key, value in update_data.items():

            setattr(
                product,
                key,
                value,
            )

        db.commit()

        db.refresh(product)

        return product

    except HTTPException:

        db.rollback()

        raise

    except Exception as e:

        db.rollback()

        print(
            "UPDATE PRODUCT ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Unable to update product"
                ),
                "error": str(e),
            },
        )


# =========================================================
# DELETE PRODUCT
# =========================================================

@router.delete(
    "/{product_id}",
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_authenticated_user
    ),
):

    try:

        product = (
            db.query(Product)
            .filter(
                Product.id == product_id
            )
            .first()
        )

        if not product:

            raise HTTPException(
                status_code=404,
                detail="Product not found",
            )

        # -------------------------------------------------
        # AUTHORIZATION
        # -------------------------------------------------

        authorize_merchant_product(
            product,
            current_user,
        )

        # -------------------------------------------------
        # DELETE
        # -------------------------------------------------

        db.delete(product)

        db.commit()

        return {
            "message": (
                "Product deleted successfully"
            ),
            "product_id": product_id,
        }

    except HTTPException:

        db.rollback()

        raise

    except Exception as e:

        db.rollback()

        print(
            "DELETE PRODUCT ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Unable to delete product"
                ),
                "error": str(e),
            },
        )