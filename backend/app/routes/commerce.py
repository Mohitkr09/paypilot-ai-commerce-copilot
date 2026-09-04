from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db

from app.services.commerce_agent_service import (
    CommerceAgentService,
)

from app.services.gemini_service import (
    GeminiService,
)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/commerce",
    tags=["AI Commerce"],
)


# =========================================================
# HEALTH CHECK
# =========================================================

@router.get("/health")
def commerce_health():
    """
    Check whether the AI Commerce Agent is running.
    """

    return {
        "success": True,
        "status": "healthy",
        "module": "ai_commerce_agent",
    }


# =========================================================
# GEMINI HEALTH CHECK
# =========================================================

@router.get("/gemini-health")
def gemini_health():
    """
    Check Gemini configuration.

    This does not make an API request.
    """

    try:

        result = GeminiService.health_check()

        return {
            "success": True,
            **result,
        }

    except Exception as e:

        print(
            "GEMINI HEALTH ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Gemini health check failed",
                "error": str(e),
            },
        )


# =========================================================
# GEMINI TEST
# =========================================================

@router.get("/gemini-test")
def gemini_test():
    """
    Test Gemini independently from the commerce database.

    Example:

        GET /commerce/gemini-test
    """

    try:

        response = GeminiService.chat(
            "Say hello to the PayPilot AI Commerce Agent "
            "in one short sentence."
        )

        return {
            "success": True,
            "provider": "Google Gemini",
            "response": response,
        }

    except Exception as e:

        print(
            "GEMINI TEST ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Gemini test failed",
                "error": str(e),
            },
        )


# =========================================================
# GET PRODUCT CATALOG
# =========================================================

@router.get("/catalog")
def get_catalog(
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of products",
    ),
    db: Session = Depends(get_db),
):
    """
    Return an AI-readable product catalog.

    Example:

        GET /commerce/catalog?limit=20
    """

    try:

        products = (
            CommerceAgentService.get_catalog(
                db=db,
                limit=limit,
            )
        )

        catalog = (
            CommerceAgentService.build_catalog(
                products
            )
        )

        return {
            "success": True,
            "count": len(catalog),
            "products": catalog,
        }

    except Exception as e:

        print(
            "COMMERCE CATALOG ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to load product catalog",
                "error": str(e),
            },
        )


# =========================================================
# SEARCH PRODUCTS
# =========================================================

@router.get("/search")
def search_products(
    q: Optional[str] = Query(
        default=None,
        description="Product search query",
    ),

    category: Optional[str] = Query(
        default=None,
        description="Product category",
    ),

    min_price: Optional[float] = Query(
        default=None,
        ge=0,
        description="Minimum price",
    ),

    max_price: Optional[float] = Query(
        default=None,
        ge=0,
        description="Maximum price",
    ),

    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of products",
    ),

    db: Session = Depends(get_db),
):
    """
    Search products from the merchant catalog.

    Examples:

        GET /commerce/search?q=laptop

        GET /commerce/search?q=phone&max_price=50000

        GET /commerce/search?category=electronics
    """

    try:

        # -------------------------------------------------
        # Validate price range
        # -------------------------------------------------

        if (
            min_price is not None
            and max_price is not None
            and min_price > max_price
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "min_price cannot be greater "
                    "than max_price"
                ),
            )

        # -------------------------------------------------
        # Search
        # -------------------------------------------------

        products = (
            CommerceAgentService.search_products(
                db=db,
                query=q,
                category=category,
                min_price=min_price,
                max_price=max_price,
                limit=limit,
            )
        )

        catalog = (
            CommerceAgentService.build_catalog(
                products
            )
        )

        return {
            "success": True,
            "query": q,
            "category": category,
            "min_price": min_price,
            "max_price": max_price,
            "count": len(catalog),
            "products": catalog,
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "COMMERCE SEARCH ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Product search failed",
                "error": str(e),
            },
        )


# =========================================================
# GET SINGLE PRODUCT
# =========================================================

@router.get("/products/{product_id}")
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    Get one product from the merchant catalog.

    Example:

        GET /commerce/products/1
    """

    try:

        product = (
            CommerceAgentService.get_product(
                db=db,
                product_id=product_id,
            )
        )

        if not product:

            raise HTTPException(
                status_code=404,
                detail="Product not found",
            )

        product_data = (
            CommerceAgentService.product_to_dict(
                product
            )
        )

        return {
            "success": True,
            "product": product_data,
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "GET COMMERCE PRODUCT ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to load product",
                "error": str(e),
            },
        )


# =========================================================
# PRODUCT RECOMMENDATIONS
# =========================================================

@router.get("/recommend")
def recommend_products(
    q: Optional[str] = Query(
        default=None,
        description="What the customer is looking for",
    ),

    category: Optional[str] = Query(
        default=None,
        description="Product category",
    ),

    max_price: Optional[float] = Query(
        default=None,
        ge=0,
        description="Maximum customer budget",
    ),

    limit: int = Query(
        default=5,
        ge=1,
        le=20,
        description="Maximum recommendations",
    ),

    db: Session = Depends(get_db),
):
    """
    Return deterministic product recommendations.

    Examples:

        GET /commerce/recommend?q=laptop

        GET /commerce/recommend?q=gaming%20laptop&max_price=80000
    """

    try:

        result = (
            CommerceAgentService.recommend_products(
                db=db,
                query=q,
                category=category,
                max_price=max_price,
                limit=limit,
            )
        )

        return {
            "success": True,
            "query": q,
            "category": category,
            "max_price": max_price,
            **result,
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "COMMERCE RECOMMENDATION ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Product recommendation failed",
                "error": str(e),
            },
        )


# =========================================================
# AI COMMERCE CHAT
# =========================================================

@router.post("/chat")
def commerce_chat(
    message: str = Query(
        ...,
        min_length=1,
        description=(
            "Customer's natural-language "
            "commerce query"
        ),
    ),

    limit: int = Query(
        default=10,
        ge=1,
        le=20,
        description="Maximum products used by the agent",
    ),

    db: Session = Depends(get_db),
):
    """
    Main AI Commerce endpoint.

    Example:

        POST /commerce/chat?message=I%20need%20a%20laptop%20under%2080000

    Flow:

        Customer
            ↓
        Natural language
            ↓
        Budget/category extraction
            ↓
        Product database
            ↓
        Recommendation engine
            ↓
        Verified catalog
            ↓
        Gemini
            ↓
        Conversational response
    """

    try:

        message = message.strip()

        if not message:

            raise HTTPException(
                status_code=400,
                detail="Commerce message cannot be empty",
            )

        result = (
            CommerceAgentService.process_query(
                db=db,
                user_message=message,
                limit=limit,
            )
        )

        return {
            "success": True,
            **result,
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "COMMERCE CHAT ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Commerce agent failed",
                "error": str(e),
            },
        )


# =========================================================
# AI CATALOG CONTEXT
# =========================================================

@router.get("/catalog/context")
def get_catalog_context(
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum products in AI context",
    ),

    db: Session = Depends(get_db),
):
    """
    Convert product catalog into AI-readable context.

    Example:

        GET /commerce/catalog/context
    """

    try:

        products = (
            CommerceAgentService.get_catalog(
                db=db,
                limit=limit,
            )
        )

        context = (
            CommerceAgentService.build_catalog_context(
                products
            )
        )

        return {
            "success": True,
            "count": len(products),
            "context": context,
        }

    except Exception as e:

        print(
            "COMMERCE CONTEXT ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Unable to build AI catalog context"
                ),
                "error": str(e),
            },
        )