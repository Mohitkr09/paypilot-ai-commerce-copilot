# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

from dotenv import load_dotenv

load_dotenv()


# =========================================================
# STANDARD LIBRARY
# =========================================================

import os
from datetime import datetime
from typing import Any


# =========================================================
# FASTAPI
# =========================================================

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware


# =========================================================
# PYDANTIC
# =========================================================

from pydantic import BaseModel


# =========================================================
# SQLALCHEMY
# =========================================================

from sqlalchemy import text


# =========================================================
# DATABASE
# =========================================================

from app.db.database import (
    Base,
    engine,
    SessionLocal,
)


# =========================================================
# MODELS
# =========================================================

from app.models import (
    Merchant,
    Product,
    Order,
    Payment,
    ManualReview,
    AuditLog,
    Settings,
    RiskEvaluation,
    Campaign,
)


# =========================================================
# ROUTES
# =========================================================

# Product API
from app.api.product import (
    router as product_router,
)

# Authentication
from app.routes.auth import (
    router as auth_router,
)

# Product CRUD
from app.routes.product import (
    router as product_crud_router,
)

# Merchant
from app.routes.merchant import (
    router as merchant_router,
)

# Policy
from app.routes.policy import (
    router as policy_router,
)

# Offers
from app.routes.offer import (
    router as offer_router,
)

# Orders
from app.routes.order import (
    router as order_router,
)

# Payments
from app.routes.payments import (
    router as payment_router,
)

# Manual Reviews
from app.routes.manual_review import (
    router as manual_review_router,
)

# Settings
from app.routes.settings import (
    router as settings_router,
)

# Risk Analytics
from app.routes.risk_analytics import (
    router as risk_analytics_router,
)

# Risk Evaluation
from app.routes.risk_evaluation import (
    router as risk_evaluation_router,
)

# Audit Logs
from app.routes.audit_log import (
    router as audit_log_router,
)

# Real-Time Events
from app.routes.events import (
    router as events_router,
)

# Analytics
from app.routes.analytics import (
    router as analytics_router,
)

# AI Commerce Agent
from app.routes.commerce import (
    router as commerce_router,
)

# AI Order / PayPilot Agent
from app.routes.agent import (
    router as agent_router,
)

# AI Campaign Orchestrator
from app.routes.campaign import (
    router as campaign_router,
)


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

Base.metadata.create_all(
    bind=engine
)


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="PayPilot AI",
    description=(
        "AI-powered commerce, payment risk, "
        "transaction management, analytics, "
        "AI-assisted shopping, and campaign "
        "orchestration platform"
    ),
    version="0.2.0",
)


# =========================================================
# CORS
# =========================================================

ALLOWED_ORIGINS = [
    # Local development
    "http://localhost:5173",
    "http://127.0.0.1:5173",

    # Production - Vercel
    "https://paypilot-ai-commerce-copilot.vercel.app",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# =========================================================
# REGISTER ROUTES
# =========================================================

# Product API
app.include_router(
    product_router
)

# Product CRUD
app.include_router(
    product_crud_router
)

# Merchant
app.include_router(
    merchant_router
)

# Policy
app.include_router(
    policy_router
)

# Offers
app.include_router(
    offer_router
)

# Orders
app.include_router(
    order_router
)

# Payments
app.include_router(
    payment_router
)

# Manual Reviews
app.include_router(
    manual_review_router
)

# Settings
app.include_router(
    settings_router
)

# Authentication
app.include_router(
    auth_router
)

# Risk Analytics
app.include_router(
    risk_analytics_router
)

# Risk Evaluation
app.include_router(
    risk_evaluation_router
)

# Audit Logs
app.include_router(
    audit_log_router
)

# Real-Time SSE Events
app.include_router(
    events_router
)

# Analytics
app.include_router(
    analytics_router
)

# AI Commerce Agent
app.include_router(
    commerce_router
)

# AI Order / PayPilot Agent
app.include_router(
    agent_router
)

# AI Campaign Orchestrator
app.include_router(
    campaign_router
)


# =========================================================
# ROOT ENDPOINT
# =========================================================

@app.get("/")
def root():

    return {
        "message": "PayPilot AI API is running",
        "version": "0.2.0",
        "status": "online",

        "modules": [
            "products",
            "merchants",
            "policies",
            "offers",
            "orders",
            "payments",
            "manual_reviews",
            "risk_evaluation",
            "risk_analytics",
            "analytics",
            "audit_logs",
            "real_time_events",
            "ai_commerce_agent",
            "ai_order_agent",
            "campaign_orchestrator",
        ],
    }


# =========================================================
# GENERAL HEALTH CHECK
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "paypilot-ai",
        "version": "0.2.0",
    }


# =========================================================
# CORS DEBUG ENDPOINT
# =========================================================

@app.get("/cors-test")
def cors_test():

    return {
        "status": "cors_ok",
        "message": "CORS middleware is active",
    }


# =========================================================
# DEBUG CATALOG
# =========================================================
#
# Temporary endpoint used to inspect the Render database.
#
# It shows:
# - merchants
# - merchant policies
# - products
# - stock
# - product status
#
# Remove this endpoint after deployment/debugging is complete.
# =========================================================

@app.get("/debug/catalog")
def debug_catalog():

    db = SessionLocal()

    try:

        # -------------------------------------------------
        # Fetch merchants
        # -------------------------------------------------

        merchants = db.query(Merchant).all()

        # -------------------------------------------------
        # Fetch products
        # -------------------------------------------------

        products = db.query(Product).all()

        # -------------------------------------------------
        # Return database information
        # -------------------------------------------------

        return {
            "status": "success",

            "merchant_count": len(
                merchants
            ),

            "product_count": len(
                products
            ),

            "merchants": [
                {
                    "id": merchant.id,

                    "name": getattr(
                        merchant,
                        "name",
                        None,
                    ),

                    "email": getattr(
                        merchant,
                        "email",
                        None,
                    ),

                    "maximum_discount_percent": getattr(
                        merchant,
                        "maximum_discount_percent",
                        None,
                    ),

                    "minimum_margin": getattr(
                        merchant,
                        "minimum_margin",
                        None,
                    ),

                    "auto_payment_limit": getattr(
                        merchant,
                        "auto_payment_limit",
                        None,
                    ),

                    "bundle_allowed": getattr(
                        merchant,
                        "bundle_allowed",
                        None,
                    ),

                    "is_active": getattr(
                        merchant,
                        "is_active",
                        None,
                    ),
                }

                for merchant in merchants
            ],

            "products": [
                {
                    "id": product.id,

                    "name": getattr(
                        product,
                        "name",
                        None,
                    ),

                    "price": getattr(
                        product,
                        "price",
                        None,
                    ),

                    "cost_price": getattr(
                        product,
                        "cost_price",
                        None,
                    ),

                    "category": getattr(
                        product,
                        "category",
                        None,
                    ),

                    "description": getattr(
                        product,
                        "description",
                        None,
                    ),

                    # Compatibility with older model versions
                    "stock": getattr(
                        product,
                        "stock",
                        None,
                    ),

                    "stock_quantity": getattr(
                        product,
                        "stock_quantity",
                        None,
                    ),

                    "sku": getattr(
                        product,
                        "sku",
                        None,
                    ),

                    "is_active": getattr(
                        product,
                        "is_active",
                        None,
                    ),

                    "merchant_id": getattr(
                        product,
                        "merchant_id",
                        None,
                    ),
                }

                for product in products
            ],
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e),
        }

    finally:

        db.close()


# =========================================================
# CATALOG IMPORT SCHEMA
# =========================================================

class CatalogImportRequest(BaseModel):
    """
    Payload used for temporary local -> Render
    catalog migration.

    Only merchants and products are transferred.
    """

    merchants: list[dict[str, Any]]

    products: list[dict[str, Any]]


# =========================================================
# DATETIME HELPER
# =========================================================

def parse_datetime(
    value: Any,
):
    """
    Convert ISO datetime strings into Python datetime objects.

    Supports:
    - None
    - datetime
    - ISO datetime string
    """

    if value is None:
        return None

    if isinstance(
        value,
        datetime,
    ):
        return value

    if isinstance(
        value,
        str,
    ):

        try:

            return datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00",
                )
            )

        except ValueError:

            return None

    return None


# =========================================================
# DEBUG IMPORT TOKEN
# =========================================================
#
# Set this ONLY in Render Environment:
#
# DEBUG_IMPORT_TOKEN=your-secret
#
# Do NOT put the actual secret in this source code.
# =========================================================

DEBUG_IMPORT_TOKEN = os.getenv(
    "DEBUG_IMPORT_TOKEN",
    "",
)


# =========================================================
# TEMPORARY CATALOG IMPORT
# =========================================================
#
# Local transfer script sends:
#
# X-Import-Token: <same secret>
#
# After migration is complete:
#
# 1. Remove this endpoint.
# 2. Remove DEBUG_IMPORT_TOKEN from Render.
# =========================================================

@app.post("/debug/import-catalog")
def import_catalog(
    data: CatalogImportRequest,

    x_import_token: str | None = Header(
        default=None,
        alias="X-Import-Token",
    ),
):

    # -----------------------------------------------------
    # Check whether import feature is configured
    # -----------------------------------------------------

    if not DEBUG_IMPORT_TOKEN:

        raise HTTPException(
            status_code=503,
            detail=(
                "Catalog import is not configured."
            ),
        )

    # -----------------------------------------------------
    # Validate token
    # -----------------------------------------------------

    if (
        not x_import_token
        or x_import_token
        != DEBUG_IMPORT_TOKEN
    ):

        raise HTTPException(
            status_code=401,
            detail=(
                "Unauthorized catalog import request."
            ),
        )

    # -----------------------------------------------------
    # Create database session
    # -----------------------------------------------------

    db = SessionLocal()

    try:

        # =================================================
        # CHECK EXISTING DATA
        # =================================================

        existing_merchants = (
            db.query(Merchant).count()
        )

        existing_products = (
            db.query(Product).count()
        )

        # -------------------------------------------------
        # Prevent duplicate migration
        # -------------------------------------------------

        if (
            existing_merchants > 0
            or existing_products > 0
        ):

            return {
                "status": "skipped",

                "message": (
                    "Render catalog already "
                    "contains data. "
                    "No records were imported."
                ),

                "merchant_count": (
                    existing_merchants
                ),

                "product_count": (
                    existing_products
                ),
            }

        # =================================================
        # INSERT MERCHANTS
        # =================================================

        merchant_count = 0

        for merchant_data in data.merchants:

            merchant = Merchant(

                id=merchant_data[
                    "id"
                ],

                name=merchant_data[
                    "name"
                ],

                email=merchant_data[
                    "email"
                ],

                password_hash=merchant_data.get(
                    "password_hash"
                ),

                role=merchant_data.get(
                    "role",
                    "merchant",
                ),

                is_active=merchant_data.get(
                    "is_active",
                    True,
                ),

                maximum_discount_percent=merchant_data.get(
                    "maximum_discount_percent",
                    10.0,
                ),

                minimum_margin=merchant_data.get(
                    "minimum_margin",
                    300.0,
                ),

                auto_payment_limit=merchant_data.get(
                    "auto_payment_limit",
                    3000.0,
                ),

                bundle_allowed=merchant_data.get(
                    "bundle_allowed",
                    True,
                ),

                created_at=parse_datetime(
                    merchant_data.get(
                        "created_at"
                    )
                ),

                updated_at=parse_datetime(
                    merchant_data.get(
                        "updated_at"
                    )
                ),
            )

            db.add(
                merchant
            )

            merchant_count += 1

        # -------------------------------------------------
        # Flush merchants
        # -------------------------------------------------

        db.flush()

        # =================================================
        # INSERT PRODUCTS
        # =================================================

        product_count = 0

        for product_data in data.products:

            product = Product(

                id=product_data[
                    "id"
                ],

                merchant_id=product_data[
                    "merchant_id"
                ],

                name=product_data[
                    "name"
                ],

                category=product_data[
                    "category"
                ],

                description=product_data.get(
                    "description"
                ),

                price=product_data[
                    "price"
                ],

                cost_price=product_data[
                    "cost_price"
                ],

                stock_quantity=product_data.get(
                    "stock_quantity",
                    0,
                ),

                sku=product_data[
                    "sku"
                ],

                is_active=product_data.get(
                    "is_active",
                    True,
                ),
            )

            db.add(
                product
            )

            product_count += 1

        # -------------------------------------------------
        # Flush products
        # -------------------------------------------------

        db.flush()

        # =================================================
        # RESET MERCHANT ID SEQUENCE
        # =================================================
        #
        # We preserve the original IDs during migration.
        # Therefore PostgreSQL's sequence needs to be
        # moved to the current maximum ID.
        # =================================================

        db.execute(
            text(
                """
                SELECT setval(
                    pg_get_serial_sequence(
                        'merchants',
                        'id'
                    ),
                    COALESCE(
                        (
                            SELECT MAX(id)
                            FROM merchants
                        ),
                        1
                    ),
                    true
                )
                """
            )
        )

        # =================================================
        # RESET PRODUCT ID SEQUENCE
        # =================================================

        db.execute(
            text(
                """
                SELECT setval(
                    pg_get_serial_sequence(
                        'products',
                        'id'
                    ),
                    COALESCE(
                        (
                            SELECT MAX(id)
                            FROM products
                        ),
                        1
                    ),
                    true
                )
                """
            )
        )

        # =================================================
        # COMMIT
        # =================================================

        db.commit()

        # =================================================
        # SUCCESS RESPONSE
        # =================================================

        return {
            "status": "success",

            "message": (
                "Catalog imported successfully."
            ),

            "merchant_count": (
                merchant_count
            ),

            "product_count": (
                product_count
            ),
        }

    except Exception:

       

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Catalog import failed. "
                "The database transaction "
                "was rolled back."
            ),
        )

    finally:

        db.close()