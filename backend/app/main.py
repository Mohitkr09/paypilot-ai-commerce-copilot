from dotenv import load_dotenv

# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================
#
# Loads variables from backend/.env
#
# Example:
#
# GEMINI_API_KEY=your_gemini_api_key
# GEMINI_MODEL=gemini-3.7-flash
#
# =========================================================

load_dotenv()


# =========================================================
# FASTAPI
# =========================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


# =========================================================
# DATABASE
# =========================================================

from app.db.database import Base, engine


# =========================================================
# MODELS
# =========================================================
#
# IMPORTANT:
#
# Import every model before create_all().
# This ensures SQLAlchemy knows about every table.
#
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
    Campaign,                 # NEW - Phase 1 Campaign Orchestrator
)


# =========================================================
# ROUTES
# =========================================================


# ---------------------------------------------------------
# Product API
# ---------------------------------------------------------

from app.api.product import (
    router as product_router,
)


# ---------------------------------------------------------
# Authentication
# ---------------------------------------------------------

from app.routes.auth import (
    router as auth_router,
)


# ---------------------------------------------------------
# Product CRUD
# ---------------------------------------------------------

from app.routes.product import (
    router as product_crud_router,
)


# ---------------------------------------------------------
# Merchant
# ---------------------------------------------------------

from app.routes.merchant import (
    router as merchant_router,
)


# ---------------------------------------------------------
# Policy
# ---------------------------------------------------------

from app.routes.policy import (
    router as policy_router,
)


# ---------------------------------------------------------
# Offers
# ---------------------------------------------------------

from app.routes.offer import (
    router as offer_router,
)


# ---------------------------------------------------------
# Orders
# ---------------------------------------------------------

from app.routes.order import (
    router as order_router,
)


# ---------------------------------------------------------
# Payments
# ---------------------------------------------------------

from app.routes.payments import (
    router as payment_router,
)


# ---------------------------------------------------------
# Manual Reviews
# ---------------------------------------------------------

from app.routes.manual_review import (
    router as manual_review_router,
)


# ---------------------------------------------------------
# Settings
# ---------------------------------------------------------

from app.routes.settings import (
    router as settings_router,
)


# ---------------------------------------------------------
# Risk Analytics
# ---------------------------------------------------------

from app.routes.risk_analytics import (
    router as risk_analytics_router,
)


# ---------------------------------------------------------
# Risk Evaluation
# ---------------------------------------------------------
#
# Evaluates individual orders using RiskService.
#
# Endpoints:
#
# POST /risk-evaluations/{order_id}
# GET  /risk-evaluations/{order_id}
#
# ---------------------------------------------------------

from app.routes.risk_evaluation import (
    router as risk_evaluation_router,
)


# ---------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------

from app.routes.audit_log import (
    router as audit_log_router,
)


# ---------------------------------------------------------
# Real-Time Events
# ---------------------------------------------------------

from app.routes.events import (
    router as events_router,
)


# =========================================================
# ANALYTICS
# =========================================================
#
# PayPilot dashboard analytics.
#
# Endpoints:
#
# GET /analytics/overview
# GET /analytics/orders
# GET /analytics/risk
# GET /analytics/manual-reviews
# GET /analytics/payments
# GET /analytics/discounts
# GET /analytics/inventory
# GET /analytics/daily
# GET /analytics/order-trend
# GET /analytics/revenue-trend
# GET /analytics/merchants
# GET /analytics/recent-activity
# GET /analytics/dashboard
#
# =========================================================

from app.routes.analytics import (
    router as analytics_router,
)


# =========================================================
# AI COMMERCE AGENT
# =========================================================
#
# Existing commerce assistant.
#
# Endpoints:
#
# GET  /commerce/health
# GET  /commerce/catalog
# GET  /commerce/catalog/context
# GET  /commerce/search
# GET  /commerce/products/{product_id}
# GET  /commerce/recommend
# POST /commerce/chat
#
# =========================================================

from app.routes.commerce import (
    router as commerce_router,
)


# =========================================================
# AI ORDER / PAYPILOT AGENT
# =========================================================
#
# Conversational PayPilot order agent.
#
# Endpoint:
#
# POST /agent/chat
#
# Flow:
#
# User message
#      ↓
# AgentService
#      ↓
# Product detection
#      ↓
# OrderCreate
#      ↓
# create_order_internal()
#      ↓
# LangGraph
#      ↓
# Policy Agent
#      ↓
# Decision Agent
#      ↓
# Risk Agent
#      ↓
# Payment Gate
#      ↓
# Audit Agent
#
# =========================================================

from app.routes.agent import (
    router as agent_router,
)


# =========================================================
# AI CAMPAIGN ORCHESTRATOR
# =========================================================
#
# Phase 1:
#
# Generates merchant campaign proposals.
#
# IMPORTANT:
#
# Phase 1 ONLY creates campaign proposals.
#
# It does NOT:
# - activate campaigns
# - modify product prices
# - apply discounts
# - create orders
# - create payments
# - move money
#
# Future phases:
#
# Phase 2 → Policy + Margin Engine
# Phase 3 → Merchant Approval
# Phase 4 → Audit Trail
# Phase 5 → Graceful Rejection
# Phase 6 → Upsell/Cross-sell Integration
#
# Endpoints:
#
# POST /campaigns/
# GET  /campaigns/
# GET  /campaigns/{campaign_id}
# DELETE /campaigns/{campaign_id}
#
# =========================================================

from app.routes.campaign import (
    router as campaign_router,
)


# =========================================================
# DATABASE INITIALIZATION
# =========================================================
#
# All models must be imported before create_all().
#
# Campaign is imported above so SQLAlchemy also creates
# the campaigns table.
#
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
#
# Frontend:
#
# Vite / React
# http://localhost:5173
#
# =========================================================

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
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


# ---------------------------------------------------------
# Product API
# ---------------------------------------------------------

app.include_router(
    product_router
)


# ---------------------------------------------------------
# Product CRUD
# ---------------------------------------------------------

app.include_router(
    product_crud_router
)


# ---------------------------------------------------------
# Merchant
# ---------------------------------------------------------

app.include_router(
    merchant_router
)


# ---------------------------------------------------------
# Policy
# ---------------------------------------------------------

app.include_router(
    policy_router
)


# ---------------------------------------------------------
# Offers
# ---------------------------------------------------------

app.include_router(
    offer_router
)


# ---------------------------------------------------------
# Orders
# ---------------------------------------------------------

app.include_router(
    order_router
)


# ---------------------------------------------------------
# Payments
# ---------------------------------------------------------

app.include_router(
    payment_router
)


# ---------------------------------------------------------
# Manual Reviews
# ---------------------------------------------------------

app.include_router(
    manual_review_router
)


# ---------------------------------------------------------
# Settings
# ---------------------------------------------------------

app.include_router(
    settings_router
)


# ---------------------------------------------------------
# Authentication
# ---------------------------------------------------------

app.include_router(
    auth_router
)


# ---------------------------------------------------------
# Risk Analytics
# ---------------------------------------------------------

app.include_router(
    risk_analytics_router
)


# ---------------------------------------------------------
# Risk Evaluation
# ---------------------------------------------------------
#
# Payment/order risk evaluation.
#
# POST:
# /risk-evaluations/{order_id}
#
# GET:
# /risk-evaluations/{order_id}
#
# ---------------------------------------------------------

app.include_router(
    risk_evaluation_router
)


# ---------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------

app.include_router(
    audit_log_router
)


# ---------------------------------------------------------
# Real-Time SSE Events
# ---------------------------------------------------------

app.include_router(
    events_router
)


# ---------------------------------------------------------
# Analytics
# ---------------------------------------------------------

app.include_router(
    analytics_router
)


# ---------------------------------------------------------
# AI Commerce Agent
# ---------------------------------------------------------

app.include_router(
    commerce_router
)


# ---------------------------------------------------------
# AI Order / PayPilot Agent
# ---------------------------------------------------------

app.include_router(
    agent_router
)


# ---------------------------------------------------------
# AI Campaign Orchestrator
# ---------------------------------------------------------
#
# Phase 1:
# Campaign proposal generation and management.
#
# ---------------------------------------------------------

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